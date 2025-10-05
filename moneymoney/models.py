from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction, connection
from django.db.models import prefetch_related_objects, Case, When, Sum, Value, Subquery, F, Window, Min, Max, DateField, OuterRef, ExpressionWrapper, DurationField, FloatField
from django.db.models.functions import FirstValue, LastValue, ExtractMonth, ExtractYear, Cast, Extract

from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils import timezone
from moneymoney import ios, functions
from moneymoney.reusing.decorators import ptimeit
from moneymoney.types import eConcept, eProductType, eOperationType
from pydicts import lod_ymv, casts, lod
from pydicts.currency import Currency

Decimal
ptimeit

RANGE_RECOMENDATION_CHOICES =( 
    (1, "All"), 
    (2, "SMA 10, 50, 200"), 
    (3, "SMA 100"), 
    (4, "Strict SMA 10, 50, 200"), 
    (5, "Strict SMA 100"), 
    (6, "Strict SMA 10, 100"), 
    (7, "None"), 
    (8, "SMA 10"), 
    (9, "SMA 5"), 
    (10, "HMA 10"), 
)



class Accounts(models.Model):
    name = models.TextField(blank=True, null=True)
    banks = models.ForeignKey('Banks',  models.DO_NOTHING, related_name="accounts", blank=False, null=False)
    active = models.BooleanField(blank=False, null=False)
    number = models.CharField(max_length=24, blank=True, null=True)
    currency = models.TextField(blank=False,  null=False, choices=settings.CURRENCIES_CHOICES)
    decimals=models.IntegerField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'accounts'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
                
    @staticmethod
    def post_payload(name="New account", banks="http://testserver/api/banks/3/", active=True, number="01234567890123456789", currency="EUR", decimals=2):
        return {
            "name": name, 
            "banks":banks, 
            "active":active, 
            "number":number, 
            "currency":currency, 
            "decimals": decimals, 
        }

    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('accounts-detail', args=(id, )))
        
    def fullName(self):
        return "{} ({})".format(_(self.name), _(self.banks.name))
        
    def is_deletable(self):
        """Función que devuelve un booleano si una cuenta es borrable, es decir, que no tenga registros dependientes."""
        if self.id==4:#Cash
            return False
            
        if (
                Accountsoperations.objects.filter(accounts_id=self.id).exists() or
                Creditcards.objects.filter(accounts_id=self.id).exists() or
                Investments.objects.filter(accounts_id=self.id).exists()
            ):
            return False
        return True

    ## @return Tuple (balance_account_currency | balance_user_currency)
    def balance(self, dt,  currency_user):
        r={}
        b=Accountsoperations.objects.filter(accounts=self, datetime__lte=dt).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
        if b is None:
            r["balance_account_currency"]=Decimal('0')
        else:
            r["balance_account_currency"]=b
        factor=Quotes.get_currency_factor(dt, self.currency, currency_user, None)
        r["balance_user_currency"]=r["balance_account_currency"]*factor
        return r

    @staticmethod
    def accounts_balance(qs, dt, currency_user):
        """
            qs. Queryset Accounts
            balance_account_currency can be calculated if all accounts in qs has the same currency
        """
        currencies_in_qs=Accounts.currencies(qs)
        r={}
        if len(currencies_in_qs)==1: #One currency only
            b=Accountsoperations.objects.filter(accounts__in=qs, datetime__lte=dt).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
            if b is None:
                r["balance_account_currency"]=Decimal('0')
            else:
                r["balance_account_currency"]=b
            factor=Quotes.get_currency_factor(dt, currencies_in_qs[0], currency_user, None)
            r["balance_user_currency"]=r["balance_account_currency"]*factor
        else:
            r["balance_account_currency"]=None
            r["balance_user_currency"]=Decimal("0")
            for currency in currencies_in_qs:
                b=Accountsoperations.objects.filter(accounts__in=qs, datetime__lte=dt, accounts__currency=currency).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
                factor=Quotes.get_currency_factor(dt, currency, currency_user, None)
                r["balance_user_currency"]=r["balance_user_currency"]+b*factor
        return r

                
            
    @staticmethod
    def currencies(qs=None):
        """
        Returns a list with distinct currencies in accounts
        """
        if qs  is None:
            return list(Accounts.objects.order_by().values_list("currency",flat=True).distinct())
        else:
            return list(qs.order_by().values_list("currency",flat=True).distinct())
        
    def amount_string(self, value):
        """
            Returns a string rounded to the number of decimals of this account

            Args:
                value (number): Any number

            Returns:
                str
        """
        return Currency(value, self.currency).string(self.decimals)

class Operationstypes(models.Model):
    name = models.TextField()

    class Meta:
        managed = True
        db_table = 'operationstypes'
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

## This model is not in Xulpymoney to avoid changing a lot of code
class Stockmarkets(models.Model):
    name = models.TextField(blank=False, null=False)
    country=models.CharField(max_length=5, blank=False, null=False)
    starts=models.TimeField(blank=False, null=False)
    closes=models.TimeField(blank=False, null=False)
    starts_futures=models.TimeField(blank=False, null=False)
    closes_futures=models.TimeField(blank=False, null=False)
    zone=models.TextField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'stockmarkets'

    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)
        
    ## Returns the close time of a given date
    def dtaware_closes(self, date):

        return casts.dtaware(date, self.closes, self.zone)
    
    def dtaware_closes_futures(self, date):
        return casts.dtaware(date, self.closes_futures, self.zone)

    def dtaware_today_closes_futures(self):
        return self.dtaware_closes_futures(date.today())
    
    ## Returns a datetime with timezone with the todays stockmarket closes
    def dtaware_today_closes(self):
        return self.dtaware_closes(date.today())

    ## Returns the starttime of a given date
    def dtaware_starts(self, date):
        return casts.dtaware(date, self.starts, self.zone)
    ## Returns a datetime with timezone with the todays stockmarket closes
    def dtaware_today_starts(self):
        return casts.dtaware(date.today(), self.starts, self.zone)


    ## When we don't know the datetime of a quote because the webpage we are scrapping doesn't gives us, we can use this functions
    ## - If it's saturday or sunday it returns last friday at close time
    ## - If it's not weekend and it's after close time it returns todays close time
    ## - If it's not weekend and it's before open time it returns yesterday close time. If it's monday it returns last friday at close time
    ## - If it's not weekend and it's after opent time and before close time it returns aware current datetime
    ## @param delay Boolean that if it's True (default) now  datetime is minus 15 minutes. If False uses now datetime
    ## @return Datetime aware, always. It can't be None
    def estimated_datetime_for_intraday_quote(self, delay=True):
        if delay==True:
            now=casts.dtaware_now(self.zone)-timedelta(minutes=15)
        else:
            now=casts.dtaware_now(self.zone)
        if now.weekday()<5:#Weekday
            if now>self.dtaware_today_closes():
                return self.dtaware_today_closes()
            elif now<self.dtaware_today_starts():
                if now.weekday()>0:#Tuesday to Friday
                    return casts.dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
                else: #Monday
                    return casts.dtaware(date.today()-timedelta(days=3), self.closes, self.zone)
            else:
                return now
        elif now.weekday()==5:#Saturday
            return casts.dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
        elif now.weekday()==6:#Sunday
            return casts.dtaware(date.today()-timedelta(days=2), self.closes, self.zone)

    ## When we don't know the date pf a quote of a one quote by day product. For example funds... we'll use this function
    ## - If it's saturday or sunday it returns last thursday at close time
    ## - If it's not weekend and returns yesterday close time except if it's monday that returns last friday at close time
    ## @return Datetime aware, always. It can't be None
    def estimated_datetime_for_daily_quote(self):
        now=casts.dtaware_now(self.zone)
        if now.weekday()<5:#Weekday
            if now.weekday()>0:#Tuesday to Friday
                return casts.dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
            else: #Monday
                return casts.dtaware(date.today()-timedelta(days=3), self.closes, self.zone)
        elif now.weekday()==5:#Saturday
            return casts.dtaware(date.today()-timedelta(days=2), self.closes, self.zone)
        elif now.weekday()==6:#Sunday
            return casts.dtaware(date.today()-timedelta(days=3), self.closes, self.zone)


class Accountsoperations(models.Model):
    concepts = models.ForeignKey('Concepts', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    datetime = models.DateTimeField(blank=False, null=False)
    associated_transfer=models.ForeignKey("Accountstransfers", models.DO_NOTHING, blank=True, null=True)
    associated_cc=models.ForeignKey("Creditcards", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'accountsoperations'
        
    def __str__(self):
        return functions.string_oneline_object(self)
        
    def __repr__(self):
        return functions.string_oneline_object(self)
        


    @staticmethod
    def post_payload(accounts="http://testserver/api/accounts/4/",  concepts="http://testserver/api/concepts/1/", amount=1000,  comment="Opening account", datetime=None):
        if datetime is None:
            dt=timezone.now()
        else:
            dt=datetime
        return {
            "concepts":concepts, 
            "amount": amount, 
            "comment": comment, 
            "accounts": accounts, 
            "datetime": dt, 
        }

    def is_editable(self):
        if self.concepts is None:
            return False
        if self.concepts.id in (eConcept.BuyShares, eConcept.SellShares, 
            eConcept.Dividends, eConcept.CreditCardBilling, eConcept.AssistancePremium,
            eConcept.DividendsSaleRights, eConcept.BondsCouponRunPayment, eConcept.BondsCouponRunIncome, 
            eConcept.BondsCoupon, eConcept.RolloverPaid, eConcept.RolloverReceived):
            return False
        if self.associated_transfer is not None:
            return False
        return True
        
    def nice_comment(self):
        if self.associated_transfer is not None:
            if self.concepts.id==eConcept.TransferOrigin:
                return _("Transfer to {0}. {1}").format(self.associated_transfer.destiny.fullName(), self.comment)
            if self.concepts.id==eConcept.TransferDestiny:
                return _("Transfer from {0}. {1}").format(self.associated_transfer.origin.fullName(), self.comment)
            if self.concepts.id==eConcept.BankCommissions:
                return _("Transfer of {0} from {1} to {2}. {3}").format( 
                    self.associated_transfer.origin.amount_string(self.associated_transfer.amount),
                    self.associated_transfer.origin.fullName(), 
                    self.associated_transfer.destiny.fullName(), 
                    self.comment)
        
        elif self.concepts.id==eConcept.CreditCardBilling:
            qs=self.paid_accountsoperations.all().select_related("creditcards")
            if len(qs)>0:
                cc_name=qs[0].creditcards.name
            else:
                cc_name=""
            return  _("Billing {} movements of {}").format(len(qs), cc_name)
            
        elif hasattr(self, "dividends"):
            return _( "From {}. Gross {}. Net {}.".format(
                self.dividends.investments.name, 
                self.dividends.investments.accounts.amount_string(self.dividends.gross), 
                self.dividends.investments.accounts.amount_string(self.dividends.net))
            )
        
        elif hasattr(self,  "investmentsoperations"):
            return _("{}: {} shares. Amount: {}. Comission: {}. Taxes: {}").format(
                self.investmentsoperations.investments.name, 
                self.investmentsoperations.investments.shares_string(self.investmentsoperations.shares),
                self.investmentsoperations.investments.accounts.amount_string(self.investmentsoperations.shares*self.investmentsoperations.price),  
                self.investmentsoperations.investments.accounts.amount_string(self.investmentsoperations.commission), 
                self.investmentsoperations.investments.accounts.amount_string(self.investmentsoperations.taxes)
            )

        return self.comment

class Banks(models.Model):
    name = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'banks'      

    def __str__(self):
        return self.name  
        
    @staticmethod
    def post_payload(name="Bank for testing", active=True):
        return {
            "name": name, 
            "active": active, 
        }

    def balance_accounts(self):
        if hasattr(self, "_balance_accounts") is False:
            qs=Accounts.objects.all().filter(banks_id=self.id, active=True)
            self._balance_accounts=Accounts.accounts_balance(qs,  timezone.now(), 'EUR')["balance_user_currency"]
        return self._balance_accounts

    def balance_investments(self, request):
        if hasattr(self, "_balance_investments") is False:
            plio=ios.IOS.from_qs(timezone.now(), request.user.profile.currency, self.investments(active=True), 3)
            self._balance_investments=plio.sum_total_io_current()["balance_user"]
        return self._balance_investments
        
    def balance_total(self, request):
        return self.balance_accounts()+self.balance_investments(request)

    def investments(self, active):
        investments= Investments.objects.all().select_related("products","products__productstypes","accounts").filter(accounts__banks__id=self.id, active=active)
        return investments

    def is_deletable(self):
        if self.id==3:#Personal management
            return False
            
        if Accounts.objects.filter(banks_id=self.id).exists() :
            return False
        return True

class Concepts(models.Model):
    name = models.TextField(blank=True, null=True)
    operationstypes = models.ForeignKey('Operationstypes', models.DO_NOTHING, blank=True, null=True)
    editable = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'concepts'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return "{} - {}".format(_(self.name), _(self.operationstypes.name))
        
    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('concepts-detail', args=(id, )))
    
    def get_used(self):
        return   Creditcardsoperations.objects.filter(concepts__id=self.id).count() + Accountsoperations.objects.filter(concepts__id=self.id).count() + Dividends.objects.filter(concepts__id=self.id).count()   

    def is_migrable(self):
        r=False
        # With data and includes expenses and incomes
        if self.operationstypes.id in [1,2] and self.id not in [1, 6, 37, 38,39,59,62,63,65,66, 67, 72, 75, 76, 77]:
           r= True
        return r

    @staticmethod
    def dictionary():
        dict_concepts={}
        for c in Concepts.objects.all():
            dict_concepts[c.id]=c
        return dict_concepts
        
    @staticmethod
    def post_payload(name="New concept", operationstypes="http://testserver/api/operationstypes/1/", editable=True):
        return {
            "name": name, 
            "operationstypes": operationstypes, 
            "editable": editable
        }

class Creditcards(models.Model):
    name = models.TextField()
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    deferred = models.BooleanField()
    maximumbalance = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    active = models.BooleanField()
    number = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'creditcards'

    def is_deletable(self):
        """Función que devuelve un booleano si una cuenta es borrable, es decir, que no tenga registros dependientes."""           
        if self.deferred==False:
            return True
        
        if Creditcardsoperations.objects.filter(creditcards_id=self.id).exists():
            return False
        return True
        
    @staticmethod
    def post_payload(name="New credit card", accounts="http://testserver/api/accounts/4/", deferred=True, maximumbalance=1000, active=True, number="12341234123412341243"):
        return {
            "name": name, 
            "accounts": accounts, 
            "deferred": deferred, 
            "maximumbalance": maximumbalance, 
            "active": active, 
            "number": number, 
        }

class Creditcardsoperations(models.Model):
    concepts = models.ForeignKey(Concepts, models.DO_NOTHING)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    creditcards = models.ForeignKey(Creditcards, models.DO_NOTHING)
    paid = models.BooleanField()
    paid_datetime = models.DateTimeField(blank=True, null=True)
    accountsoperations= models.ForeignKey(Accountsoperations, models.DO_NOTHING, null=True,  related_name="paid_accountsoperations")
    datetime = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'creditcardsoperations'
        
    @staticmethod
    def post_payload(
        creditcards="http://testserver/api/creditcards/1/",  
        concepts="http://testserver/api/concepts/1/", 
        amount=1000,  
        comment="CCO Comment", 
        datetime=timezone.now(), 
        paid=False, 
        paid_datetime=None
    ):
        return {
            "concepts":concepts, 
            "amount": amount, 
            "comment": comment, 
            "creditcards": creditcards, 
            "datetime": datetime, 
            "paid": paid, 
            "paid_datetime": paid_datetime, 
        }


class Dividends(models.Model):
    investments = models.ForeignKey('Investments', models.DO_NOTHING)
    gross = models.DecimalField(max_digits=100, decimal_places=2)
    taxes = models.DecimalField(max_digits=100, decimal_places=2)
    net = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    dps = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    datetime = models.DateTimeField(blank=True, null=True)
    accountsoperations = models.OneToOneField("Accountsoperations", models.DO_NOTHING, null=True)
    commission = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    concepts = models.ForeignKey(Concepts, models.DO_NOTHING)
    currency_conversion = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        managed = True
        db_table = 'dividends'


    @staticmethod
    def post_payload( investments="http://testserver/api/investments/1/", 
                                    gross=1000, 
                                    taxes=210, 
                                    net=790, 
                                    dps=0.1, 
                                    datetime=None, 
                                    accountsoperations=None, 
                                    commission=10, 
                                    concepts="http://testserver/api/concepts/39/", 
                                    currency_conversion=1
    ):
        if datetime is None:
            datetime=timezone.now()
        return {
            "investments": investments,
            "gross": gross, 
            "taxes": taxes, 
            "net":net, 
            "dps": dps, 
            "datetime":datetime, 
            "accountsoperations": accountsoperations, 
            "commission": commission, 
            "concepts": concepts, 
            "currency_conversion":currency_conversion, 
        }

    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('dividends-detail', args=(id, )))
        
    @transaction.atomic
    def delete(self):
        self.accountsoperations.delete()
        super().delete()

    @staticmethod
    def lod_ym_netgains_dividends(request,  dt_from=None,  dt_to=None, ids=None):
        """
            Returns a list of rows with a structure as in lod_ymv.lod_ymv_transposition
            if dt_from and dt_to is not None only shows this range dividends, else all database registers
            if ids is None returns all investments dividends, else return some investments ids List of ids
        """
            
        ld=[]
        for currency in Accounts.currencies():
            d=Dividends.objects.filter(investments__accounts__currency=currency)
            if ids is not None:
                d=d.filter(investments__id__in=ids)
            if dt_from is not None:
                d=d.filter(datetime__gte=dt_from)
            if dt_to is not None:
                d=d.filter(datetime__lte=dt_to)
            
            d=d.values("datetime__year","datetime__month").annotate(sum=Sum("net"))
            for o in  d:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(casts.dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["sum"], currency, request.user.profile.currency)})
        return lod_ymv.lod_ymv_transposition(ld)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.commission <0 or self.taxes<0:
            raise _("Taxes and commissions must be equal or greater than zero")
            return 
        
        if self.accountsoperations is None:#Insert
            c=Accountsoperations()
            c.datetime=self.datetime
            c.concepts=self.concepts
            c.amount=self.net
            #c.comment="Transaction not finished"
            c.comment=""
            c.accounts=self.investments.accounts
            c.save()
            self.accountsoperations=c
        else:#update
            self.accountsoperations.datetime=self.datetime
            self.accountsoperations.concepts=self.concepts
            self.accountsoperations.amount=self.net
            self.accountsoperations.comment=""
            self.accountsoperations.accounts=self.investments.accounts
            self.accountsoperations.save()
        models.Model.save(self)


class Investments(models.Model):
    name = models.TextField()
    active = models.BooleanField()
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    selling_price = models.DecimalField(max_digits=100, decimal_places=6)
    products = models.ForeignKey('Products', models.DO_NOTHING, blank=False, null=False)
    selling_expiration = models.DateField(blank=True, null=True)
    daily_adjustment = models.BooleanField()
    balance_percentage = models.DecimalField(max_digits=18, decimal_places=6)
    decimals=models.IntegerField(blank=False, null=False, default=6) #Refers to shares decimals

    class Meta:
        managed = True
        db_table = 'investments'
        ordering = ['name']
        

    def __str__(self):
        return self.fullName()

    def quote_string(self, value):
        """
            Returns a string with Currency.string ouput with self.products.decimals. 
        """
        return Currency(value, self.products.currency).string(self.products.decimals)
    
    def shares_string(self,value):
        """ 
            Returns a string with the number of shares round to investments.decimals

            Args:
                value (number): Any number
        """
        return str(round(value,self.decimals))


    def fullName(self):
        return "{} ({})".format(self.name, self.accounts.name)
    
    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('investments-detail', args=(id, )))


    @staticmethod
    def post_payload(name="Investment for testing", active="True", accounts="http://testserver/api/accounts/4/", selling_price=0, products="http://testserver/api/products/79329/", selling_expiration=None, daily_adjustment=False, balance_percentage=100, decimals=6):
        return {
            "name": name,
            "active": active, 
            "accounts": accounts, 
            "selling_price":selling_price, 
            "products": products, 
            "selling_expiration":selling_expiration, 
            "daily_adjustment": daily_adjustment, 
            "balance_percentage": balance_percentage, 
            "decimals": decimals, 
        }

    ## Función que devuelve un booleano si una cuenta es borrable, es decir, que no tenga registros dependientes.
    def is_deletable(self):
        if (
                Investmentsoperations.objects.filter(investments_id=self.id).exists() or
                Dividends.objects.filter(investments_id=self.id).exists() or
                Orders.objects.filter(investments_id=self.id).exists()
            ):
            return False
        return True

    def hasSameAccountCurrency(self):
        """
            Returns a boolean
            Check if investment currency is the same that account currency
        """
        if self.products.currency==self.accounts.currency:
            return True
        return False
        
        
    def selling_expiration_alert(self):
        if self.selling_price is None:
            return False
        if self.selling_price==Decimal(0):
            return False
        if self.selling_expiration is None:
            return False
        if self.selling_expiration<date.today():
            return True
        return False


    def queryset_for_investments_products_combos_order_by_fullname():
        ids=[]
        for investment in sorted(Investments.objects.select_related('accounts').select_related('products').filter(products__obsolete=False), key=lambda o: (o.fullName(), o.accounts.name)):
            ids.append(investment.id)
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
        queryset = Investments.objects.select_related('accounts').filter(pk__in=ids).order_by(preserved)
        return queryset
        
    def shares_from_db_investmentsoperations(self):        
        r=Investmentsoperations.objects.filter(investments=self).aggregate(Sum("shares"))["shares__sum"]
        if r is None:
            r=Decimal(0)
        return r

    def set_attributes_after_investmentsoperations_crud(self):      
#        print("setting investment attributes")
        # Always activeive after investmentsoperations CRUD
        if self.active is False:
            self.active=True
        # Changes selling expiration after investmentsoperations CRUD y 0 shares
        if self.selling_expiration is not None and self.selling_expiration>=date.today() and self.shares_from_db_investmentsoperations()==0:
            self.selling_expiration=date.today()-timedelta(days=1)
        self.save()
        

    @staticmethod
    def currencies():
        """
        Returns a list with distinct currencies in accounts
        """
        return list(Investments.objects.order_by().values_list("products__currency",flat=True).distinct())
        
class Investmentsoperations(models.Model):
    operationstypes = models.ForeignKey(Operationstypes, models.DO_NOTHING, blank=False, null=False)
    investments = models.ForeignKey(Investments, models.DO_NOTHING, blank=False, null=False)
    shares = models.DecimalField(max_digits=100, decimal_places=6, blank=False, null=False)
    taxes = models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False)
    commission = models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False)
    price = models.DecimalField(max_digits=100, decimal_places=6, blank=False, null=False)
    datetime = models.DateTimeField(blank=False, null=False)
    comment = models.TextField(blank=True, null=True)
    currency_conversion = models.DecimalField(max_digits=30, decimal_places=10, blank=False, null=False)
    associated_ao=models.OneToOneField("Accountsoperations", models.DO_NOTHING, blank=True, null=True)
    associated_it=models.ForeignKey("Investmentstransfers", models.DO_NOTHING, blank=True, null=True)


    class Meta:
        managed = True
        db_table = 'investmentsoperations'
        
    def __str__(self):
        return functions.string_oneline_object(self)

    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('investmentsoperations-detail', args=(id, )))


    def nice_comment(self):
        if self.associated_it is not None:
            return _("{0} transfer from '{1}' to '{2}' started at {3}. {4}").format(
                self.investments.products.productstypes.fullName(),#Same for both investments in investments transfer
                self.associated_it.investments_origin.fullName(),
                self.associated_it.investments_destiny.fullName(),
                self.associated_it.datetime_origin,
                "" if self.comment is None else self.comment)

    @staticmethod
    def post_payload(investments="http://testserver/api/investments/1/", datetime=timezone.now(), shares=1000, price=10,  taxes=0, commission=0,  operationstypes="http://testserver/api/operationstypes/4/", currency_conversion=1):
        return {
            "operationstypes": operationstypes, 
            "investments": investments, 
            "shares": shares, 
            "taxes":taxes, 
            "commission": commission, 
            "price": price, 
            "datetime": datetime, 
            "comment": "", 
            "currency_conversion": currency_conversion, 
        }

    def clean(self):
        #Checks investment has quotes
        if not Quotes.objects.filter(products=self.investments.products).exists():
            raise ValidationError(_("Investment operation can't be created because its related product hasn't quotes."))


    @transaction.atomic
    def delete(self):
        investment=self.investments
        if self.associated_ao is not None:
            self.associated_ao.delete()
        super().delete()
        investment.set_attributes_after_investmentsoperations_crud()

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
            This save must use self.fullClean when used as a model
        """
        self.full_clean()
        super(Investmentsoperations, self).save(*args, **kwargs) #To generate io and then plio

        if self.associated_ao and self.associated_ao.id is not None:
            self.associated_ao.delete()
            self.associated_ao = None
        
        # No associated ao if daily_adjustment
        if self.investments.daily_adjustment is True: #Because it uses adjustment information
            return
        
        # Updates asociated ao
        plio=ios.IOS.from_ids(timezone.now(), "EUR", [self.investments.id, ], 1) #I set EUR to reuse this code but __user values will not be used
        #Searches io investments operations of the comment
        io=None
        for o in plio.d_io(self.investments.id):
            if o["id"]==self.id:
                io=o
        
        if self.operationstypes.id==eOperationType.SharesPurchase:#Compra Acciones
            c=Accountsoperations()
            c.datetime=self.datetime
            c.concepts_id=eConcept.BuyShares
            c.amount=-io['net_account']
            c.comment=self.comment
            c.accounts=self.investments.accounts
            c.save()
            self.associated_ao=c
        elif self.operationstypes.id==eOperationType.SharesSale:#// Venta Acciones
            c=Accountsoperations()
            c.datetime=self.datetime
            c.concepts=Concepts.objects.get(pk=eConcept.SellShares)
            c.amount=io['net_account']
            c.comment=self.comment
            c.accounts=self.investments.accounts
            c.save()
            self.associated_ao=c
        elif self.operationstypes.id in [eOperationType.SharesAdd, eOperationType.TransferFunds]:
            if self.commission!=0:#No associated_ao
                c=Accountsoperations()
                c.datetime=self.datetime
                c.concepts=Concepts.objects.get(pk=eConcept.BankCommissions)
                c.amount=-io['taxes_account']-io['commission_account']
                c.comment=self.comment
                c.accounts=self.investments.accounts
                c.save()
                self.associated_ao=c

        
        super(Investmentsoperations, self).save(update_fields=['associated_ao']) #Forces and update to avoid double insert a integrity key error



class Investmentstransfers(models.Model):
    """
        If datetime_destiny is null, transfers hasn't finished
        investments_destiny is known
    """
    datetime_origin = models.DateTimeField(blank=False, null=False)
    investments_origin= models.ForeignKey('Investments', models.CASCADE, blank=False, null=False, related_name="origin")
    shares_origin=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False) #Can be positive and negative
    price_origin=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(Decimal(0))])
    commission_origin=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(Decimal(0))], default=0)
    taxes_origin=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(Decimal(0))], default=0)
    currency_conversion_origin = models.DecimalField(max_digits=30, decimal_places=10, blank=False, null=False, validators=[MinValueValidator(Decimal(0))], default=1)

    datetime_destiny = models.DateTimeField(blank=True, null=True, default=None)
    investments_destiny= models.ForeignKey('Investments', models.CASCADE, blank=False, null=False, related_name="destiny")
    shares_destiny=models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True) #Can be positive and negative
    price_destiny=models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal(0))])
    commission_destiny=models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal(0))], default=0)
    taxes_destiny=models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal(0))], default=0)
    currency_conversion_destiny  = models.DecimalField(max_digits=30, decimal_places=10, blank=True, null=True, validators=[MinValueValidator(Decimal(0))], default=1)

    comment=models.TextField(blank=True, null=False)


    @staticmethod
    def post_payload(
        datetime_origin=timezone.now(), 
        investments_origin="http://testserver/api/investments/1/", 
        shares_origin=-1000, 
        price_origin=10, 
        commission_origin=0, 
        taxes_origin=0, 
        currency_conversion_origin=1,   
        datetime_destiny=timezone.now(), 
        investments_destiny="http://testserver/api/investments/1/",         
        shares_destiny=1000, 
        price_destiny=10, 
        commission_destiny=0, 
        taxes_destiny=0, 
        currency_conversion_destiny=1,   
        comment=""
    ):
        return {
            "datetime_origin": datetime_origin,
            "investments_origin": investments_origin,
            "shares_origin": shares_origin,
            "price_origin": price_origin,  
            "commission_origin": commission_origin, 
            "taxes_origin": taxes_origin, 
            "currency_conversion_origin": currency_conversion_origin,   
            "datetime_destiny": datetime_destiny,
            "investments_destiny": investments_destiny,         
            "shares_destiny": shares_destiny, 
            "price_destiny": price_destiny, 
            "commission_destiny": commission_destiny, 
            "taxes_destiny": taxes_destiny, 
            "currency_conversion_destiny": currency_conversion_destiny,   
            "comment": comment, 
        }

    def clean(self):
        if self.finished() is True:
            if not self.investments_origin.products.productstypes==self.investments_destiny.products.productstypes:
                raise ValidationError(_("Investment transfer can't be created if products types are not the same"))
            
            if self.investments_origin.id==self.investments_destiny.id:
                raise ValidationError(_("Investment transfer can't be created if investments are the same"))
            
            if not functions.have_different_sign(self.shares_origin, self.shares_destiny):
                raise ValidationError(_("Shares amount can't be of the same sign"))



    class Meta:
        managed = True
        db_table = 'investmentstransfers'
        
    def __str__(self):
        return functions.string_oneline_object(self)
    

    def origin_investmentoperation(self):
        try:
            return Investmentsoperations.objects.get(associated_it=self, operationstypes_id=eOperationType.TransferSharesOrigin)
        except:
            return None
    
    def destiny_investmentoperation(self):
        try:
            return Investmentsoperations.objects.get(associated_it=self, operationstypes_id=eOperationType.TransferSharesDestiny)
        except:
            return None 
        
    def finished(self):
        """
            Boolean to know if an IT is finished
        """
        return False if self.datetime_destiny is None else True
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        ## Creates Investmentstransfer and generates id
        self.full_clean()
        super(Investmentstransfers, self).save(*args, **kwargs)
        
        ## Create or update origin
        origin_io=self.origin_investmentoperation()
        if origin_io is None:
            origin_io=Investmentsoperations()
        origin_io.datetime=self.datetime_origin
        origin_io.operationstypes_id=eOperationType.TransferSharesOrigin
        origin_io.investments=self.investments_origin
        origin_io.shares=self.shares_origin
        origin_io.price=self.price_origin
        origin_io.commission=self.commission_origin
        origin_io.taxes=self.taxes_origin
        origin_io.currency_conversion=self.currency_conversion_origin
        origin_io.associated_it=self
        origin_io.save()

        destiny_io=self.destiny_investmentoperation()
        if self.datetime_destiny is None: #IT unfinished. destiny_io must be deleted
            if destiny_io is not None:
                destiny_io.delete()
        else:
            ## Create or update destiny
            if destiny_io is None:
                destiny_io=Investmentsoperations()
            destiny_io.datetime=self.datetime_destiny
            destiny_io.operationstypes_id=eOperationType.TransferSharesDestiny
            destiny_io.investments=self.investments_destiny
            destiny_io.shares=self.shares_destiny
            destiny_io.price=self.price_destiny
            destiny_io.commission=self.commission_destiny
            destiny_io.taxes=self.taxes_destiny
            destiny_io.currency_conversion=self.currency_conversion_destiny
            destiny_io.associated_it=self
            destiny_io.save()

    def origin_gross_amount(self):
        return Currency(self.price_origin*self.shares_origin*self.investments_origin.products.real_leveraged_multiplier(), self.investments_origin.products.currency)

    def destiny_gross_amount(self):
        return Currency(self.price_destiny*self.shares_destiny*self.investments_destiny.products.real_leveraged_multiplier(), self.investments_destiny.products.currency)
    


    
class Leverages(models.Model):
    name = models.TextField()
    multiplier = models.DecimalField(max_digits=100, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'leverages'

    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

class Orders(models.Model):
    date = models.DateField(blank=False, null=False)
    expiration = models.DateField(blank=True, null=True) #An order can be permanent in some brokers
    shares = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    price = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    investments = models.ForeignKey(Investments, models.DO_NOTHING)
    executed = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'orders'
        
    def currency_amount(self):
        return Currency(self.price*self.shares*self.investments.products.real_leveraged_multiplier(), self.investments.products.currency)

            
        
    def needs_stop_loss_warning(self):
        if self.shares>0 and self.price>self.investments.products.basic_results()["last"]:
            return True
        elif  self.shares<0 and self.price<self.investments.products.basic_results()["last"]:
            return True
        return False

    @staticmethod
    def post_payload(date_=timezone.now().date(), expiration=None, shares=100,  price=10,  investments="http://testserver/api/investments/1/", executed=None):
        return {
            "date": date_,
            "expiration": expiration, 
            "shares": shares, 
            "price":price, 
            "investments": investments, 
            "executed":executed, 
        }

class ProductsStrategies(models.Model):
    name = models.CharField(max_length=10,  blank=False, null=False)

    class Meta:
        managed = True


class Products(models.Model):
    """
        En este modelo se integran SistemProducts y PersonalProducts, para no generar dos tablas
        Se van a respetar los 100.000.000 primeros ids para productos de sistema
        El resto serán para personal products
        La generación de ids de system products será manual asistida
        
        Antes los tenia los system products con id<0 pero fallan las fixtures al iniciar una base de datos desde zero
        
    """
    name = models.TextField(blank=True, null=True)
    isin = models.TextField(blank=True, null=True)
    currency = models.TextField(blank=False,  null=False, choices=settings.CURRENCIES_CHOICES)
    productstypes = models.ForeignKey('Productstypes', models.DO_NOTHING, blank=True, null=True)
    agrupations = models.TextField(blank=True, null=True)
    web = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    mail = models.TextField(blank=True, null=True)
    percentage = models.IntegerField(blank=False, null=False)
    productsstrategies=models.ForeignKey('Productsstrategies', models.DO_NOTHING, blank=False, null=False)
    leverages = models.ForeignKey(Leverages, models.DO_NOTHING)
    stockmarkets = models.ForeignKey(Stockmarkets, models.DO_NOTHING)
    comment = models.TextField(blank=True, null=True)
    obsolete = models.BooleanField()
    ticker_google = models.TextField(blank=True, null=True) 
    ticker_yahoo = models.TextField(blank=True, null=True) 
    ticker_morningstar = models.TextField(blank=True, null=True) 
    ticker_quefondos = models.TextField(blank=True, null=True) 
    ticker_investingcom = models.TextField(blank=True, null=True) 
    decimals = models.IntegerField(blank=True, null=True) #Refers to quotes decimals

    class Meta:
        managed = True
        db_table = 'products'
        ordering = ['name']

    def __str__(self):
        return self.fullName()
                        
    @staticmethod
    def post_system_payload(
        name="New system product", 
        isin="ES000000000",  
        currency="EUR", 
        productstypes="http://testserver/api/productstypes/2/", 
        agrupations="", 
        web="www.gentoo.org", 
        address="My street", 
        phone="9898989898", 
        mail="mailme@mail.com",
        percentage=100, 
        productsstrategies="http://testserver/api/productsstrategies/1/", 
        leverages="http://testserver/api/leverages/2/", 
        stockmarkets="http://testserver/api/stockmarkets/2/", 
        comment="System product comment", 
        obsolete=False, 
        ticker_google="", 
        ticker_yahoo="", 
        ticker_morningstar="", 
        ticker_quefondos="", 
        ticker_investingcomn="", 
        decimals=2
        ):
        return {
            "name": name, 
            "isin":isin, 
            "currency":currency, 
            "productstypes":productstypes, 
            "agrupations":agrupations, 
            "web":web, 
            "address":address, 
            "phone":phone, 
            "mail":mail, 
            "percentage":percentage, 
            "productsstrategies":productsstrategies, 
            "leverages":leverages, 
            "stockmarkets":stockmarkets, 
            "comment":comment, 
            "obsolete":obsolete, 
            "ticker_google":ticker_google, 
            "ticker_yahoo":ticker_yahoo, 
            "ticker_morningstar":ticker_morningstar, 
            "ticker_quefondos":ticker_quefondos, 
            "ticker_investingcomn":ticker_investingcomn, 
            "decimals": decimals, 
            "system": True
        }    
        
    @staticmethod
    def post_personal_payload(
        name="New personal product", 
        isin="ES000000000",  
        currency="EUR", 
        productstypes="http://testserver/api/productstypes/2/", 
        agrupations="", 
        web="www.gentoo.org", 
        address="My street", 
        phone="9898989898", 
        mail="mailme@mail.com",
        percentage=100, 
        productsstrategies="http://testserver/api/productsstrategies/1/", 
        leverages="http://testserver/api/leverages/2/", 
        stockmarkets="http://testserver/api/stockmarkets/2/", 
        comment="Personal product comment", 
        obsolete=False, 
        ticker_google="", 
        ticker_yahoo="", 
        ticker_morningstar="", 
        ticker_quefondos="", 
        ticker_investingcomn="", 
        decimals=2, 
        ):
        return {
            "name": name, 
            "isin":isin, 
            "currency":currency, 
            "productstypes":productstypes, 
            "agrupations":agrupations, 
            "web":web, 
            "address":address, 
            "phone":phone, 
            "mail":mail, 
            "percentage":percentage, 
            "productsstrategies":productsstrategies, 
            "leverages":leverages, 
            "stockmarkets":stockmarkets, 
            "comment":comment, 
            "obsolete":obsolete, 
            "ticker_google":ticker_google, 
            "ticker_yahoo":ticker_yahoo, 
            "ticker_morningstar":ticker_morningstar, 
            "ticker_quefondos":ticker_quefondos, 
            "ticker_investingcomn":ticker_investingcomn, 
            "decimals": decimals, 
            "system": False # To diff from system
        }
        
    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('products-detail', args=(id, )))
        
    @staticmethod
    def qs_distinct_with_investments(only_active=True):
        """
            Get queryset with all distinct products that have investments
            if only_active is True show only active investments
        """
        qs_investments=Investments.objects.all()
        if only_active is True:
            qs_investments=qs_investments.filter(active=True)
        # Query to get quotes with that datetimes
        return Products.objects.filter(investments__id__in=Subquery(qs_investments.values("id"))).distinct()

    def fullName(self):
        return "{} ({})".format(self.name, _(self.stockmarkets.name))

    def basic_results(self):
        """
            Returns a dictionary as defined in basic_results_from_list_of_products_id
        """
        if hasattr(self, "_basic_results") is False:
            br=Products.basic_results_from_list_of_products_id([self.id, ])
            self._basic_results=br[self.id]
        return self._basic_results

    @staticmethod
    def basic_results_from_list_of_products_id(list_products_id):
        """
            This is made in two massive steps. One for last  and other for penultimate and lastyear
            Returns a dictionary that can be queried d[product_id][last|last_datetime|penultimate|penultimate_datetime|lastyear|lastyear_datetime]
        """
        def dt_needed_penultimate(products_id):
            return casts.dtaware_day_end_from_date(r_lasts[products_id][now]["datetime"].date()-timedelta(days=1), 'UTC')#Better utc to assure
        def dt_needed_lastyear(products_id):
            return casts.dtaware_year_end(r_lasts[products_id][now]["datetime"].year-1, 'UTC')
        #####
        
        r ={}
        now=timezone.now()
        lod_lasts=[]
        for products_id in list_products_id:
            #Initialize dictionary
            r[products_id]={}
            #Create lod for last
            lod_lasts.append({"datetime": now, "products_id":products_id})
        
        r_lasts=Quotes.get_quotes(lod_lasts)
        
        lod_ply=[]#penultimate and last year
        for products_id in list_products_id:
            if r_lasts[products_id][now]["datetime"] is not None:
                lod_ply.append({"datetime": dt_needed_penultimate(products_id), "products_id":products_id})
                lod_ply.append({"datetime": dt_needed_lastyear(products_id), "products_id":products_id})
        r_ply=Quotes.get_quotes(lod_ply)
        
        #Generate answer
        for products_id in list_products_id:
            r[products_id]["last"]=r_lasts[products_id][now]["quote"]
            r[products_id]["last_datetime"]=r_lasts[products_id][now]["datetime"]

            if r[products_id]["last_datetime"] is None:
                r[products_id]["penultimate"]=None 
                r[products_id]["penultimate_datetime"]=None
                r[products_id]["lastyear"]=None
                r[products_id]["lastyear_datetime"]=None
            else:
                r[products_id]["penultimate"]=r_ply[products_id][dt_needed_penultimate(products_id)]["quote"]
                r[products_id]["penultimate_datetime"]=r_ply[products_id][dt_needed_penultimate(products_id)]["datetime"]
                r[products_id]["lastyear"]=r_ply[products_id][dt_needed_lastyear(products_id)]["quote"]
                r[products_id]["lastyear_datetime"]=r_ply[products_id][dt_needed_lastyear(products_id)]["datetime"]
        return r
        
    ## IBEXA es x2 pero esta en el pricio
    ## CFD DAX no está en el precio
    def real_leveraged_multiplier(self):
        if self.productstypes.id in (eProductType.CFD, eProductType.Future):
            return self.leverages.multiplier
        return 1
        
    def ohclMonthlyBeforeSplits(self):
        if hasattr(self, "_ohcl_monthly_before_splits") is False:
        # This is the main query
            self._ohcl_monthly_before_splits = Quotes.objects.filter(
                products_id=self.id
            ).annotate(
                # 1. First, create the 'month' field that we will partition by.
                month=ExtractMonth('datetime'),
                year=ExtractYear('datetime')
            ).values(# This .values() call now defines our GROUP BY clause
                    'year', 'month').annotate(
                # 2. Next, apply all calculations as window functions.
                # This calculates the result for each row's respective month.
                # Note that Min() and Max() can also be used as window functions.
                open=Window(
                    expression=FirstValue('quote'),
                    partition_by=[F('year'),F('month')],
                    order_by=F('datetime').asc()
                ),
                high=Window(
                    expression=Max('quote'),
                    partition_by=[F('year'),F('month')]
                ),
                low=Window(
                    expression=Min('quote'),
                    partition_by=[F('year'),F('month')]
                ),
                close=Window(
                    expression=LastValue('quote'),
                    partition_by=[F('year'),F('month')],
                    order_by=F('datetime').asc()
                )
            ).values(
                # 3. Now, select only the columns we need.
                'year','month', 'open', 'high', 'low', 'close', 'products_id'
            ).distinct("year","month").order_by('year','month') # 4. Use distinct() to get one unique row per month.

        return list(self._ohcl_monthly_before_splits)

    def ohclDailyBeforeSplits(self):
        if hasattr(self, "_ohcl_daily_before_splits") is False:
            self._ohcl_daily_before_splits = Quotes.objects.filter(
                products_id=self.id
            ).annotate(
                # 1. First, create the 'month' field that we will partition by.
                date=Cast('datetime', output_field=DateField()),
            ).values('date').annotate(# This .values() call now defines our GROUP BY clause
                # 2. Next, apply all calculations as window functions.
                # This calculates the result for each row's respective month.
                # Note that Min() and Max() can also be used as window functions.
                open=Window(
                    expression=FirstValue('quote'),
                    partition_by=[F('date')],
                    order_by=F('datetime').asc()
                ),
                high=Window(
                    expression=Max('quote'),
                    partition_by=[F('date')]
                ),
                low=Window(
                    expression=Min('quote'),
                    partition_by=[F('date')]
                ),
                close=Window(
                    expression=FirstValue('quote'),
                    partition_by=[F('date')],
                    order_by=F('datetime').desc()
                )
            ).values(
                # 3. Now, select only the columns we need.
                'date', 'open', 'high', 'low', 'close', 'products_id'
            ).distinct("date").order_by('date') # 4. Use distinct() to get one unique row per month.
        return list(self._ohcl_daily_before_splits)
        
    def compare_with(self, other_product):
        """
            Compare product quotes between this product and other
            Returns a list of dictionaries ordered by datetime
        """
        from .models import Quotes
        # from django.db.models import (
        #     Subquery, OuterRef, F, FloatField, DurationField,
        #     BigIntegerField, ExpressionWrapper
        # )
        # from django.db.models.functions import Cast,Extract

        # 1. Define your two base querysets
        qs_better = Quotes.objects.filter(products=self).order_by('datetime')
        qs_worse = Quotes.objects.filter(products=other_product)

        # 2. Create two subqueries: one for the value, one for the datetime.
        # A subquery can only return a single column, so we need two.

        # Subquery to find the latest value
        subquery_value = qs_worse.filter(
            datetime__lte=OuterRef('datetime')
        ).order_by('-datetime').values('quote')[:1]

        # Subquery to find the datetime of that latest value
        subquery_datetime = qs_worse.filter(
            datetime__lte=OuterRef('datetime')
        ).order_by('-datetime').values('datetime')[:1]

        # 3. Annotate the first queryset with all calculated fields
        comparison_queryset = qs_better.annotate(
            # Get the corresponding value and datetime from the other stock
            price_better=F('quote'),
            price_worse=Subquery(subquery_value),
            datetime_worse=Subquery(subquery_datetime),
        ).annotate(
            # Calculate the time difference. The result is a DurationField
            diff=Extract(
                     ExpressionWrapper(F('datetime') - F('datetime_worse'), output_field=DurationField()
            ), "epoch"), 
            price_ratio=Cast(F('quote'), FloatField()) / Cast(F('price_worse'), FloatField())
        ).values("datetime", "price_better", "price_worse", "diff", "price_ratio").order_by("datetime")
        return list(comparison_queryset)



    @staticmethod
    def next_system_products_id():
        return Products.objects.filter(id__lt=10000000).order_by("-id")[0].id+1

class Quotes(models.Model):
    datetime = models.DateTimeField(blank=True, null=True)
    quote = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    products = models.ForeignKey(Products, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'quotes'
        
    def __str__(self):
        return f"Quote ({self.id}) of '{self.products.name}' at {self.datetime} is {self.quote}"

        
    @staticmethod
    def qs_last_quotes():
        """
            Returns a Quotes queryset with the last quotes of all products with quotes
        """
        return Quotes.objects.all().order_by(
                'products_id', 
                '-datetime'
            ).distinct(
                'products_id'
            )     

    @staticmethod
    def post_payload(products="http://testserver/api/products/79329/", datetime=None, quote=10):
        if datetime is None:
            datetime = timezone.now()
        return {
            "datetime": datetime, 
            "products": products, 
            "quote": quote, 
        }


    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.datetime-timezone.now()>timedelta(days=1):
            return _("Error saving '{0}'. Datetime it's in the future").format(self)
        quotes=Quotes.objects.filter(datetime=self.datetime, products=self.products).select_related("products")
        if quotes.exists():
            quotes.update(quote=self.quote)
            return _("Updating '{0}'").format(quotes)
        else:
            models.Model.save(self)
            return _("Inserting '{0}'").format(self)

    @staticmethod
    def hurl(request, id): ##Do not use url, conflicts with self.url in drf
        return request.build_absolute_uri(reverse('quotes-detail', args=(id, )))
    
    @staticmethod
    def get_quote(product_id, datetime_):
        """
            Gets a quote object of a product in a datetime or less.
            Returns and object or None
        """
        try:
            r=Quotes.objects.filter(products__id=product_id, datetime__lte=datetime_).order_by("-datetime")[0]
            return r
        except:
            return None
            
    @staticmethod
#    @ptimeit
    def get_quotes(lod_):
        """
            Gets a massive quote query
            
            Parameters:
                - lod_= [{"products_id": 79234, "datetime": ...}, ]
            
            Returns a dictionary {(products_id,datetime): quote, ....} or a lod
            
        """
        if len (lod_)==0:
            return {}
            
        lod_=lod.lod_remove_duplicates(lod_)
            
        list_of_qs=[]
        for needed_quote in lod_:
            list_of_qs.append(Quotes.objects.filter(products__id=needed_quote["products_id"], datetime__lte=needed_quote["datetime"]).annotate(
            needed_datetime=Value(needed_quote["datetime"], output_field=models.DateTimeField()), 
            needed_products_id=Value(needed_quote["products_id"], output_field=models.IntegerField())
            ).order_by("-datetime")[:1])
            
        ## Multiples queries  FASTER
        combined_qs=[]
        for qs in list_of_qs:
            tmplod=qs.values()
            if len(tmplod)>0:
                combined_qs.append(tmplod[0])
        r={}
        for d in combined_qs:    
            if not d["needed_products_id"] in r:
                r[d["needed_products_id"]]={}
            r[d["needed_products_id"]][d["needed_datetime"]]=d
            

        ## Union Queries SLOWER
#        
#        combined_qs=Quotes.objects.none()
#        for i in range(len(list_of_qs)):
#            combined_qs=combined_qs.union(list_of_qs[i])
#            
#        r={}
#        for d in combined_qs.values():    
#            if not d["needed_products_id"] in r:
#                r[d["needed_products_id"]]={}
#            r[d["needed_products_id"]][d["needed_datetime"]]=d
        
        #Sets missing queries to None
        for needed_quote in lod_:
            if not needed_quote["products_id"] in r:
                r[needed_quote["products_id"]]={}
            if not needed_quote["datetime"] in r[needed_quote["products_id"]]:
                r[needed_quote["products_id"]][needed_quote["datetime"]]={"datetime":None, "id":None, "quote":None, "needed_datetime":needed_quote["datetime"], "needed_products_id":needed_quote["products_id"]}
                
        return r

    
    
    @staticmethod
    def get_currency_factor(datetime_, from_, to_ ,  get_quotes_result):
        """
            Gets the factor to pass a currency to other in a datetime
            Params:
                - get_quotes_result: Dictionary result of Quotes.get_quotes. Poner None para que se calcule3
            Returns and object or None
        """
        def get_quote(products_id,  datetime_):
            if get_quotes_result is None:
                q=Quotes.get_quote(products_id, datetime_)
                if q is None:
                    return None
                else:
                    return q.quote
            else:
                return get_quotes_result[products_id][datetime_]["quote"]
        
        
        if from_==to_:
            return 1
            
        if from_== 'EUR' and to_== 'USD':
            return get_quote(74747, datetime_)
        elif from_== 'USD' and to_== 'EUR':
            q=get_quote(74747, datetime_)
            if q is None:
                return None
            else:
                if q==0:
                    return None
                else:
                    return 1/q
        print("NOT FOUND")
        return None
        
    

    
    @staticmethod
    def get_quote_dictionary_for_currency_factor(datetime_,  from_,  to_):
        """
            Returns a dictionary to be used to create the lod of get_quotes
    """
        if (from_== 'EUR' and  to_=='USD') or  (from_=="USD" and  to_=="EUR"):
            return {"products_id":74747,  "datetime":datetime_}
        print("CANT CONVERT TO GET_QUOTE DICTIONARY",  datetime_,  from_,  to_) 
#    
#        r_quotes=Quotes.get_quotes(lod_quotes)
#        
#        r_factors={}
#        for needed_factor in lod_:
#            #Initialize dictionary
#            if not needed_factor["from_"] in r_factors:
#                r_factors[needed_factor["from_"]]={}
#                if not needed_factor["to_"] in r_factors[needed_factor["from_"]]:
#                    r_factors[needed_factor["from_"]][needed_factor["to_"]]={}
#                
#            # Assign values
#            if (needed_factor["from_"]== needed_factor["to_"]):
#                r_factors[needed_factor["from_"]][needed_factor["to_"]][needed_factor["datetime"]]=1
#                
#            elif (needed_factor["from_"]== 'EUR' and  needed_factor["to_"]== 'USD'):
#                r_factors["EUR"]["USD"][needed_factor["datetime"]]=r_quotes[74747][needed_factor["datetime"]]["quote"]
#                
#            elif (needed_factor["from_"]== 'USD' and  needed_factor["to_"]== 'EUR'):
#                if r_quotes[74747][needed_factor["datetime"]]["quote"] is None:
#                    r_factors["USD"]["EUR"][needed_factor["datetime"]]=None
#                else:
#                    r_factors["USD"]["EUR"][needed_factor["datetime"]]=1/r_quotes[74747][needed_factor["datetime"]]["quote"]
#            
#            else:
#                print("MASSIVE FACTOR NOT FOUND",  needed_factor)
#        return r_factors

class Productspairs(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False)
    a = models.ForeignKey(Products, on_delete=models.DO_NOTHING, related_name='products')
    b = models.ForeignKey(Products, on_delete=models.DO_NOTHING, related_name='+')

    class Meta:
        managed = True
        db_table = 'productspairs'

class Productstypes(models.Model):
    name = models.TextField()

    class Meta:
        managed = True
        db_table = 'productstypes'
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

class Splits(models.Model):
    datetime = models.DateTimeField()
    products = models.ForeignKey(Products, models.DO_NOTHING)
    before = models.IntegerField()
    after = models.IntegerField()
    comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'splits'


class StrategiesTypes(models.IntegerChoices):
    PairsInSameAccount = 1, _('Pairs in same account')
    Ranges = 2,  _('Product ranges')
    Generic = 3, _('Generic') 
    FastOperations = 4, _('Fast operations') 



class StrategiesPairsInSameAccount(models.Model):
    strategy = models.OneToOneField("Strategies", on_delete=models.CASCADE, primary_key=True)
    worse_product = models.ForeignKey(Products, on_delete=models.DO_NOTHING, related_name='worse_product')
    better_product = models.ForeignKey(Products, on_delete=models.DO_NOTHING, related_name='better_product')
    account = models.ForeignKey(Accounts, on_delete=models.DO_NOTHING)

    class Meta:
        managed = True
        db_table = 'strategies_pairs_in_same_account'

    @staticmethod
    def post_payload(
        strategy, 
        worse_product="http://testserver/api/products/79329/", 
        better_product="http://testserver/api/products/79328/", 
        account="http://testserver/api/accounts/4/"
    ):
        return {
            "strategy": strategy,
            "worse_product": worse_product,
            "better_product": better_product,
            "account": account,
        }

class StrategiesProductsRange(models.Model):
    strategy = models.OneToOneField("Strategies", on_delete=models.CASCADE, primary_key=True)
    product = models.ForeignKey(Products, on_delete=models.DO_NOTHING)
    investments = models.ManyToManyField("Investments", blank=False)
    percentage_between_ranges = models.DecimalField(blank=False, null=False,max_digits=100, decimal_places=6)
    percentage_gains = models.DecimalField(blank=False, null=False, max_digits=100, decimal_places=6)
    amount = models.DecimalField(blank=False, null=False, max_digits=100, decimal_places=6)
    recomendation_method = models.IntegerField(choices=RANGE_RECOMENDATION_CHOICES)
    only_first = models.BooleanField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'strategies_products_range'

    @staticmethod
    def post_payload(
        strategy, 
        investments,
        product="http://testserver/api/products/79329/",
        percentage_between_ranges=0.05,
        percentage_gains=0.10,
        amount=10000,
        recomendation_method=1,
        only_first=False
    ):
        return {
            "strategy": strategy,
            "product": product,
            "investments": investments,
            "percentage_between_ranges": percentage_between_ranges,
            "percentage_gains": percentage_gains,
            "amount": amount,
            "recomendation_method": recomendation_method,
            "only_first": only_first,
        }

class StrategiesGeneric(models.Model):
    strategy = models.OneToOneField("Strategies", on_delete=models.CASCADE, primary_key=True)
    investments = models.ManyToManyField("Investments", blank=False)

    class Meta:
        managed = True
        db_table = 'strategies_generic'

    @staticmethod
    def post_payload(
        strategy, 
        investments
    ):
        return {
            "strategy": strategy,
            "investments": investments,
        }

class StrategiesFastOperations(models.Model):
    strategy = models.OneToOneField("Strategies", on_delete=models.CASCADE, primary_key=True)
    accounts = models.ManyToManyField("accounts", blank=False)

    class Meta:
        managed = True
        db_table = 'strategies_fast_operations'

    @staticmethod
    def post_payload(
        strategy, 
        accounts
    ):
        """
        Static method 

        @param strategy Dictionary with strategy object
        @param accounts List of urls
        """
        return {
            "strategy": strategy,
            "accounts": accounts,
        }


class Strategies(models.Model):
    name = models.TextField(blank=False, null=False)
    dt_from = models.DateTimeField(blank=False, null=False)
    dt_to = models.DateTimeField(blank=True, null=True)
    type = models.IntegerField(choices=StrategiesTypes.choices)
    comment = models.TextField(blank=True, null=True)
    class Meta:
        managed = True
        db_table = 'strategies'


                        
    @staticmethod
    def post_payload(
        name="New strategy", 
        dt_from=None, 
        dt_to=None, 
        type=2, 
        comment="Strategy comment", 
    ):
        return {
            "name": name, 
            "dt_from": timezone.now() if dt_from is None else dt_from, 
            "dt_to": dt_to, 
            "type":type, 
            "comment":comment,
        }

    ## Replaces None for dt_to and sets a very big datetine
    def dt_to_for_comparations(self):
        if self.dt_to is None:
            return timezone.now().replace(hour=23, minute=59)#End of the current day if strategy is not closed
        return self.dt_to
    @staticmethod
    def hurl(request, id):
        return request.build_absolute_uri(reverse('strategies-detail', args=(id, )))

class Accountstransfers(models.Model):
    datetime = models.DateTimeField(blank=False, null=False)
    origin= models.ForeignKey('Accounts', models.CASCADE, blank=False, null=False, related_name="origin")
    destiny= models.ForeignKey('Accounts', models.CASCADE,  blank=False,  null=False, related_name="destiny")
    amount=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(Decimal(0))])
    commission=models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(Decimal(0))])
    comment = models.TextField(blank=True, null=False)
    ao_origin = models.ForeignKey("Accountsoperations", models.DO_NOTHING,  blank=True,  null=True, related_name="ao_origin")
    ao_destiny = models.ForeignKey("Accountsoperations", models.DO_NOTHING,  blank=True,  null=True, related_name="ao_destiny")
    ao_commission = models.ForeignKey("Accountsoperations", models.DO_NOTHING,  blank=True,  null=True, related_name="ao_commission")
        
    class Meta:
        managed = True
        db_table = 'accountstransfers'
        
    def __str__(self):
        return functions.string_oneline_object(self)
        
        
    @transaction.atomic
    def save(self, *args, **kwargs):
        self.full_clean() #Used to apply validations
        if self.id is not None:
            Accountsoperations.objects.filter(associated_transfer=self.id).delete()
        
        self.ao_origin=Accountsoperations()
        self.ao_origin.datetime=self.datetime
        self.ao_origin.accounts=self.origin
        self.ao_origin.concepts_id=eConcept.TransferOrigin
        self.ao_origin.amount=-self.amount
        self.ao_origin.comment=self.comment
        self.ao_origin.save()
        
        self.ao_destiny=Accountsoperations()
        self.ao_destiny.datetime=self.datetime
        self.ao_destiny.accounts=self.destiny
        self.ao_destiny.concepts_id=eConcept.TransferDestiny
        self.ao_destiny.amount=self.amount
        self.ao_destiny.comment=self.comment
        self.ao_destiny.save()
        
        if self.commission!=0:
            self.ao_commission=Accountsoperations()
            self.ao_commission.datetime=self.datetime
            self.ao_commission.accounts=self.origin
            self.ao_commission.concepts_id=eConcept.BankCommissions
            self.ao_commission.amount=-self.commission
            self.ao_commission.comment=self.comment
            self.ao_commission.save()
        
        super().save(*args, **kwargs)
        self.ao_origin.associated_transfer=self
        self.ao_origin.save()
        self.ao_destiny.associated_transfer=self
        self.ao_destiny.save()
        if self.ao_commission is not None:
            self.ao_commission.associated_transfer=self
            self.ao_commission.save()
        
#        functions.print_object(self)
#        functions.print_object(self.ao_origin)
#        functions.print_object(self.ao_destiny)
#        functions.print_object(self.ao_commission)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        Accountsoperations.objects.filter(associated_transfer=self.id).delete()
        r=super().delete(*args, **kwargs)
#        print("Deleted",  r)
        return r
        
        
    @staticmethod
    def post_payload(datetime=timezone.now(),  origin="http://testserver/api/accounts/4/", destiny="http://testserver/api/accounts/6/", amount=1000, commission=10,  comment="Personal transfer" ):
        return {
            "datetime":datetime, 
            "origin": origin, 
            "destiny":destiny, 
            "amount":amount, 
            "commission":commission, 
            "comment":comment, 
        }
#
### Class who controls all comments from accountsoperations, investmentsoperations ...
#class Comment:
#    def __init__(self):
#        pass
#
#    ##Obtiene el codigo de un comment
#    def getCode(self, string):
#        (code, args)=self.get(string)
#        return code        
#
#    def getArgs(self, string):
#        """
#            Obtiene los argumentos enteros de un comment
#        """
#        (code, args)=self.get(string)
#        return args
#
#    def get(self, string):
#        """Returns (code,args)"""
#        string=string
#        try:
#            number=eval(f"[{string}]")#old string2list_of integers
#            if len(number)==1:
#                code=number[0]
#                args=[]
#            else:
#                code=number[0]
#                args=number[1:]
#            return(code, args)
#        except:
#            return(None, None)
#            
#    ## Function to generate a encoded comment using distinct parameters
#    ## Encode parameters can be:
#    ## - eComment.InvestmentOperation, hlcontract
#    ## - eComment.Dividend, dividend
#    ## - eComment.AccountTransferOrigin operaccountorigin, operaccountdestiny, operaccountorigincommission
#    ## - eComment.AccountTransferOriginCommission operaccountorigin, operaccountdestiny, operaccountorigincommission
#    ## - eComment.AccountTransferDestiny operaccountorigin, operaccountdestiny, operaccountorigincommission
#    ## - eComment.CreditCardBilling creditcard, operaccount
#    ## - eComment.CreditCardRefund opercreditcardtorefund
#    def encode(self, ecomment, *args):
#        if ecomment==eComment.InvestmentOperation:
#            return "{},{}".format(eComment.InvestmentOperation, args[0].id)
#        elif ecomment==eComment.Dividend:
#            return "{},{}".format(eComment.Dividend, args[0].id)   
#        elif ecomment==eComment.CreditCardBilling:
#            return "{},{},{}".format(eComment.CreditCardBilling, args[0].id, args[1].id)      
#        elif ecomment==eComment.CreditCardRefund:
#            return "{},{}".format(eComment.CreditCardRefund, args[0].id)        
#    
#    def validateLength(self, number, code, args):
#        if number!=len(args):
#            print("Comment {} has not enough parameters".format(code))
#            return False
#        return True
#
#    def decode(self, string):
#            if string=="":
#                return ""
##        try:
#            (code, args)=self.get(string)
#            if code==None:
#                return string
#
#            if code==eComment.InvestmentOperation:
#                io=self.decode_objects(string)
##                if io.investments.hasSameAccountCurrency():
#                return _("{}: {} shares. Amount: {}. Comission: {}. Taxes: {}").format(io.investments.name, io.shares, io.shares*io.price,  io.commission, io.taxes)
##                else:
##                    return _("{}: {} shares. Amount: {} ({}). Comission: {} ({}). Taxes: {} ({})").format(io.investment.name, io.shares, io.gross(eMoneyCurrency.Product), io.gross(eMoneyCurrency.Account),  io.money_commission(eMoneyCurrency.Product), io.money_commission(eMoneyCurrency.Account),  io.taxes(eMoneyCurrency.Product), io.taxes(eMoneyCurrency.Account))
#
#            elif code==eComment.CreditCardRefund:#Devolución de tarjeta
#                if not self.validateLength(1, code, args): return string
#                cco=Creditcardsoperations.objects.get(pk=args[0])
#                money=Currency(cco.amount, cco.creditcards.accounts.currency)
#                return _("Refund of {} payment of which had an amount of {}").format(casts.dtaware2str(cco.datetime), money)
##        except:
##            return _("Error decoding comment {}").format(string)
#
#    def decode_objects(self, string):
#        (code, args)=self.get(string)
#        if code==None:
#            return None
#
#        if code==eComment.InvestmentOperation:
#            if not self.validateLength(1, code, args): return None
#            io=Investmentsoperations.objects.select_related("investments").get(pk=args[0])
#            return io
#
#        elif code==eComment.Dividend:#Comentario de cuenta asociada al dividendo
#            if not self.validateLength(1, code, args): return None
#            try:
#                return Dividends.objects.get(pk=args[0])
#            except:
#                return None
#
#        elif code==eComment.CreditCardBilling:#Facturaci´on de tarjeta diferida
#            if not self.validateLength(2, code, args): return string
#            creditcard=Creditcards.objects.get(pk=args[0])
#            operaccount=Accountsoperations.objects.get(pk=args[1])
#            return {"creditcard":creditcard, "operaccount":operaccount}
#
#        elif code==eComment.CreditCardRefund:#Devolución de tarjeta
#            if not self.validateLength(1, code, args): return string
#            cco=Creditcardsoperations.objects.get(pk=args[0])
#            money=Currency(cco.amount, cco.creditcards.accounts.currency)
#            return _("Refund of {} payment of which had an amount of {}").format(casts.dtaware2str(cco.datetime), money)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    favorites= models.ManyToManyField(Products)
    currency = models.CharField(max_length=4,  blank=False,  null=False, choices=settings.CURRENCIES_CHOICES, default="EUR")
    zone=models.CharField(max_length=50, blank=False, null=False, default="Europe/Madrid")
    investing_com_url=models.TextField(blank=True, null=True)
    investing_com_cookie=models.TextField(blank=True, null=True)
    investing_com_referer=models.TextField(blank=True, null=True)
    invest_amount_1=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=2500)
    invest_amount_2=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=3500)
    invest_amount_3=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=7800)
    invest_amount_4=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=7800)
    invest_amount_5=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=7800)
    annual_gains_target=models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False, default=4)

    class Meta:
        managed = True
        db_table = 'profiles'

class EstimationsDps(models.Model):
    year = models.IntegerField(blank=False, null=False)
    products= models.ForeignKey(Products, models.DO_NOTHING, blank=False, null=False)
    estimation = models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False)
    date_estimation = models.DateField(blank=False, null=False, default=timezone.now)

    class Meta:
        managed = True
        db_table = 'estimations_dps'

    @staticmethod
    def post_payload(year=date.today().year,  products="http://testserver/api/products/79329/",  estimation=0.52,  date_estimation=date.today()):
        return {
            "year":year, 
            "products": products, 
            "estimation": estimation, 
            "date_estimation": date_estimation, 
        }

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.id is None and EstimationsDps.objects.filter(year=self.year, products=self.products).exists(): 
            old=EstimationsDps.objects.get(year=self.year, products=self.products)
            self.id=old.id #To update it
        models.Model.save(self)

class Dps(models.Model):
    date = models.DateField(blank=False, null=False)
    gross = models.DecimalField(max_digits=18, decimal_places=6, blank=False, null=False)
    products = models.ForeignKey(Products, models.DO_NOTHING, blank=False, null=False)
    paydate = models.DateField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'dps'


class Assets:    
    @staticmethod
    def currencies():
        """
        Returns a list with distinct currencies in accounts
        """
        return list(set(Accounts.currencies()) | set(Investments.currencies()))

    ## This method should take care of diffrent currenciesç
    ## @param month can be None to calculate all year
    def lod_ym_balance_user_by_operationstypes(request, operationstypes_id, year=None,  exclude_dividends=True):
        """
            Returns a list of rows with a structure as in lod_ymv.lod_ymv_transposition
            if year only shows this year, else all database registers
            
            Parameters:
                - request
                - Operationstypes_id,
                - year,
                - exclude_dividends. Boolean. If true excludes in Accountsoperations eConcept.dividends to avoid count them twice in Reports that use Dividends separated
        """
            
        ld=[]
        for currency in Accounts.currencies():
            ao=Accountsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, accounts__currency=currency)
            if exclude_dividends is True:
                ao=ao.exclude(concepts__id__in=eConcept.dividends())
            
            if year is not None:
                ao=ao.filter(datetime__year=year)
            
            ao=ao.values("datetime__year","datetime__month").annotate(Sum("amount")).order_by("datetime__year", "datetime__month")
            for o in  ao:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(casts.dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})

            cc=Creditcardsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, creditcards__accounts__currency=currency)
            if year is not None:
                cc=cc.filter(datetime__year=year)
            cc=cc.values("datetime__year","datetime__month").annotate(Sum("amount")) 
            for o in  cc:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(casts.dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})
        return lod_ymv.lod_ymv_transposition(ld)

    ## This method should take care of diffrent currenciesç
    ## @param month can be None to calculate all year
    def lod_ym_balance_user_by_concepts(request, concepts_ids, year=None):
        """
            Returns a list of rows with a structure as in lod_ymv.lod_ymv_transposition
            if year only shows this year, else all database registers
        """
            
        ld=[]
        for currency in Accounts.currencies():
            ao=Accountsoperations.objects.filter(concepts__id__in=concepts_ids, accounts__currency=currency)
            
            if year is not None:
                ao=ao.filter(datetime__year=year)
            
            ao=ao.values("datetime__year","datetime__month").annotate(Sum("amount")).order_by("datetime__year", "datetime__month")
            for o in  ao:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(casts.dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})

            cc=Creditcardsoperations.objects.filter(concepts__id__in=concepts_ids, creditcards__accounts__currency=currency)
            if year is not None:
                cc=cc.filter(datetime__year=year)
            cc=cc.values("datetime__year","datetime__month").annotate(Sum("amount")) 
            for o in  cc:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(casts.dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})
        return lod_ymv.lod_ymv_transposition(ld)

    @staticmethod
    def money_convert(dt, amount, from_,  to_):   
        """
            Makes a money conversion from a currency to other in a moment
        """
        factor=Quotes.get_currency_factor(dt, from_, to_, None)
        if factor is None:
            return None
        else:
            return amount*factor

        
    @staticmethod
    def pl_total_balance(dt, local_currency, mode=ios.IOSModes.sumtotals):
        """
            Returns a dict with the following keys:
            {'accounts_user': 0, 'investments_user': 0, 'total_user': 0, 'investments_invested_user': 0}
        """
        accounts_user= Accounts.accounts_balance(Accounts.objects.all(), dt, local_currency)["balance_user_currency"]
       
        plio=ios.IOS.from_all(dt,  local_currency,  mode)

        r= { 
            "accounts_user": accounts_user, 
            "investments_user": plio.sum_total_io_current()["balance_user"],
            "total_user": accounts_user+Decimal(plio.sum_total_io_current()["balance_user"]),
            "investments_invested_user": plio.sum_total_io_current()["invested_user"],
            "datetime": dt,
            }
            
        if not mode == ios.IOSModes.sumtotals:
            r["zerorisk_user"]= plio.sum_total_io_current_zerorisk_user()+accounts_user
            
        return r

class FastOperationsCoverage(models.Model):
    datetime = models.DateTimeField(blank=False, null=False)
    investments = models.ForeignKey('Investments', models.DO_NOTHING, blank=False, null=False)
    amount= models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        
