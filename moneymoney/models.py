from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Case, When, Sum
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils import timezone
from json import loads, dumps
from moneymoney.types import eComment, eConcept, eProductType, eOperationType
from moneymoney.reusing.casts import string2list_of_integers
from moneymoney.reusing.connection_dj import cursor_one_field, cursor_rows
from moneymoney.reusing.currency import Currency
from moneymoney.reusing.datetime_functions import dtaware_month_end, dtaware, dtaware2string, dtaware_day_end_from_date, dtaware_year_end
from moneymoney.reusing.percentage import Percentage, percentage_between
from moneymoney.investment_operations import t_keys_not_investment,  calculate_ios_lazy,  calculate_ios_finish, MyDjangoJSONEncoder, loads_hooks_io, loads_hooks_tb
from pydicts import lod, lod_ymv
from requests import get

Decimal

RANGE_RECOMENDATION_CHOICES =( 
    (1, "All"), 
    (2, "SMA 10, 50, 200"), 
    (3, "SMA 100"), 
    (4, "Strict SMA 10, 50, 200"), 
    (5, "Strict SMA 100"), 
    (6, "Strict SMA 10, 100"), 
    (7, "None"), 
)
PCI_CHOICES =( 
    ('c', _("Call")), 
    ('p', _("Put")), 
    ('i', _("Inline")), 
)

class Accounts(models.Model):
    name = models.TextField(blank=True, null=True)
    banks = models.ForeignKey('Banks',  models.DO_NOTHING, related_name="accounts", blank=False, null=False)
    active = models.BooleanField(blank=False, null=False)
    number = models.CharField(max_length=24, blank=True, null=True)
    currency = models.TextField()
    decimals=models.IntegerField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'accounts'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
        
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
#        r=cursor_one_row("select * from account_balance(%s,%s,%s)", (self.id, dt, local_currency))
#        return r['balance_account_currency'], r['balance_user_currency']
            
            
        r={}
        b=Accountsoperations.objects.filter(accounts=self, datetime__lte=dt).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
        if b is None:
            r["balance_account_currency"]=Decimal('0')
        else:
            r["balance_account_currency"]=b
        factor=Quotes.currency_factor(dt, self.currency, currency_user)
        r["balance_user_currency"]=r["balance_account_currency"]*factor
        return r

    @staticmethod
    def accounts_balance(qs, dt, currency_user):
        """
            qs. Queryset Accounts
            balance_account_currency can be calculated if all accounts in qs has the same currency
        """
        currencies_in_qs=list(qs.order_by().values_list("currency",flat=True).distinct())
        r={}
        if len(currencies_in_qs)==1: #One currency only
            b=Accountsoperations.objects.filter(accounts__in=qs, datetime__lte=dt).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
            if b is None:
                r["balance_account_currency"]=Decimal('0')
            else:
                r["balance_account_currency"]=b
            factor=Quotes.currency_factor(dt, currencies_in_qs[0], currency_user)
            r["balance_user_currency"]=r["balance_account_currency"]*factor
        else:
            r["balance_account_currency"]=None
            r["balance_user_currency"]=Decimal("0")
            for currency in currencies_in_qs:
                b=Accountsoperations.objects.filter(accounts__in=qs, datetime__lte=dt, accounts__currency=currency).select_related("accounts").aggregate(Sum("amount"))["amount__sum"]
                factor=Quotes.currency_factor(dt, currency, currency_user)
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

        return dtaware(date, self.closes, self.zone)
    
    def dtaware_closes_futures(self, date):
        return dtaware(date, self.closes_futures, self.zone)

    def dtaware_today_closes_futures(self):
        return self.dtaware_closes_futures(date.today())
    
    ## Returns a datetime with timezone with the todays stockmarket closes
    def dtaware_today_closes(self):
        return self.dtaware_closes(date.today())

    ## Returns the starttime of a given date
    def dtaware_starts(self, date):
        return dtaware(date, self.starts, self.zone)
    ## Returns a datetime with timezone with the todays stockmarket closes
    def dtaware_today_starts(self):
        return dtaware(date.today(), self.starts, self.zone)


    ## When we don't know the datetime of a quote because the webpage we are scrapping doesn't gives us, we can use this functions
    ## - If it's saturday or sunday it returns last friday at close time
    ## - If it's not weekend and it's after close time it returns todays close time
    ## - If it's not weekend and it's before open time it returns yesterday close time. If it's monday it returns last friday at close time
    ## - If it's not weekend and it's after opent time and before close time it returns aware current datetime
    ## @param delay Boolean that if it's True (default) now  datetime is minus 15 minutes. If False uses now datetime
    ## @return Datetime aware, always. It can't be None
    def estimated_datetime_for_intraday_quote(self, delay=True):
        if delay==True:
            now=self.zone.now()-timedelta(minutes=15)
        else:
            now=self.zone.now()
        if now.weekday()<5:#Weekday
            if now>self.dtaware_today_closes():
                return self.dtaware_today_closes()
            elif now<self.dtaware_today_starts():
                if now.weekday()>0:#Tuesday to Friday
                    return dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
                else: #Monday
                    return dtaware(date.today()-timedelta(days=3), self.closes, self.zone)
            else:
                return now
        elif now.weekday()==5:#Saturday
            return dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
        elif now.weekday()==6:#Sunday
            return dtaware(date.today()-timedelta(days=2), self.closes, self.zone)

    ## When we don't know the date pf a quote of a one quote by day product. For example funds... we'll use this function
    ## - If it's saturday or sunday it returns last thursday at close time
    ## - If it's not weekend and returns yesterday close time except if it's monday that returns last friday at close time
    ## @return Datetime aware, always. It can't be None
    def estimated_datetime_for_daily_quote(self):
        now=self.zone.now()
        if now.weekday()<5:#Weekday
            if now.weekday()>0:#Tuesday to Friday
                return dtaware(date.today()-timedelta(days=1), self.closes, self.zone)
            else: #Monday
                return dtaware(date.today()-timedelta(days=3), self.closes, self.zone)
        elif now.weekday()==5:#Saturday
            return dtaware(date.today()-timedelta(days=2), self.closes, self.zone)
        elif now.weekday()==6:#Sunday
            return dtaware(date.today()-timedelta(days=3), self.closes, self.zone)


class Accountsoperations(models.Model):
    concepts = models.ForeignKey('Concepts', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    datetime = models.DateTimeField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'accountsoperations'
        
    def __str__(self):
        return "{} {} {}".format(self.datetime, self.concepts.name, self.amount)

    def can_be_updated(self):
        if self.concepts is None:
            return False
        if self.concepts.id in (eConcept.BuyShares, eConcept.SellShares, 
            eConcept.Dividends, eConcept.CreditCardBilling, eConcept.AssistancePremium,
            eConcept.DividendsSaleRights, eConcept.BondsCouponRunPayment, eConcept.BondsCouponRunIncome, 
            eConcept.BondsCoupon, eConcept.RolloverPaid, eConcept.RolloverReceived):
            return False
        if Comment().getCode(self.comment) in (eComment.AccountTransferOrigin, eComment.AccountTransferDestiny, eComment.AccountTransferOriginCommission):
            return False        
        return True

    def is_editable(self):
        if self.concepts==None:
            return False
        if self.concepts.id in (eConcept.BuyShares, eConcept.SellShares, 
            eConcept.Dividends, eConcept.CreditCardBilling, eConcept.AssistancePremium,
            eConcept.DividendsSaleRights, eConcept.BondsCouponRunPayment, eConcept.BondsCouponRunIncome, 
            eConcept.BondsCoupon, eConcept.RolloverPaid, eConcept.RolloverReceived):
            return False
        if Comment().getCode(self.comment) in (eComment.AccountTransferOrigin, eComment.AccountTransferDestiny, eComment.AccountTransferOriginCommission):
            return False        
        return True
        
#    def is_creditcardbilling(self):
#        if self.concepts.id==eConcept.CreditCardBilling:
#            return True
#        return False
#    def is_transfer(self):
#        if Comment().getCode(self.comment) in (eComment.AccountTransferOrigin, eComment.AccountTransferDestiny, eComment.AccountTransferOriginCommission):
#            return True
#        return False
        
    def is_investmentoperation(self):
        if Comment().getCode(self.comment) in (eComment.InvestmentOperation, ):
            return True
        return False

class Banks(models.Model):
    name = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'banks'      

    def __str__(self):
        return self.name

    def balance_accounts(self):
        if hasattr(self, "_balance_accounts") is False:
            qs=Accounts.objects.all().filter(banks_id=self.id, active=True)
            self._balance_accounts=Accounts.accounts_balance(qs,  timezone.now(), 'EUR')["balance_user_currency"]
        return self._balance_accounts

    def balance_investments(self, request):
        if hasattr(self, "_balance_investments") is False:
            plio=PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, self.investments(active=True), 3)
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
    
    def get_used(self):
        return   Creditcardsoperations.objects.filter(concepts__id=self.id).count() + Accountsoperations.objects.filter(concepts__id=self.id).count() + Dividends.objects.filter(concepts__id=self.id).count()   

    def is_migrable(self):
        r=False
        # With data and includes expenses and incomes
        if self.operationstypes.id in [1,2] and self.id not in [1, 6, 37, 38,39,59,62,63,65,66, 67, 72, 75, 76, 77]:
           r= True
        return r

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


class Dividends(models.Model):
    investments = models.ForeignKey('Investments', models.DO_NOTHING)
    gross = models.DecimalField(max_digits=100, decimal_places=2)
    taxes = models.DecimalField(max_digits=100, decimal_places=2)
    net = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    dps = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    datetime = models.DateTimeField(blank=True, null=True)
    accountsoperations = models.ForeignKey(Accountsoperations, models.DO_NOTHING, null=True)
    commission = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    concepts = models.ForeignKey(Concepts, models.DO_NOTHING)
    currency_conversion = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        managed = True
        db_table = 'dividends'

    @transaction.atomic
    def delete(self):
        self.accountsoperations.delete()
        models.Model.delete(self)

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
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["sum"], currency, request.user.profile.currency)})
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
            c.comment=Comment().encode(eComment.Dividend, self)
            c.accounts=self.investments.accounts
            c.save()
            self.accountsoperations=c
        else:#update
            self.accountsoperations.datetime=self.datetime
            self.accountsoperations.concepts=self.concepts
            self.accountsoperations.amount=self.net
            self.accountsoperations.comment=Comment().encode(eComment.Dividend, self)
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

    def fullName(self):
        return "{} ({})".format(self.name, self.accounts.name)

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
        return Investmentsoperations.objects.filter(investments=self).aggregate(Sum("shares"))["shares__sum"]
        
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

    class Meta:
        managed = True
        db_table = 'investmentsoperations'
        
    def __str__(self):
        return "InvestmentOperation"

    @transaction.atomic
    def delete(self):
        concepts=Concepts.objects.filter(pk__in=(eConcept.BuyShares, eConcept.SellShares, eConcept.BankCommissions))
        qs_ao=Accountsoperations.objects.filter(concepts__in=concepts, comment=f'{eComment.InvestmentOperation},{self.id}')
        qs_ao.delete()
        models.Model.delete(self)

    ## Esta función actualiza la tabla investmentsaccountsoperations que es una tabla donde 
    ## se almacenan las accountsoperations automaticas por las operaciones con investments. Es una tabla 
    ## que se puede actualizar en cualquier momento con esta función
    @transaction.atomic
    def update_associated_account_operation(self,  request):
        concepts=Concepts.objects.filter(pk__in=(eConcept.BuyShares, eConcept.SellShares, eConcept.BankCommissions))
        qs_ao=Accountsoperations.objects.filter(concepts__in=concepts, comment=f'{eComment.InvestmentOperation},{self.id}')
        qs_ao.delete()
        plio=PlInvestmentOperations.from_ids(timezone.now(), request.user.profile.currency, [self.investments.id, ], 1)
        #Searches io investments operations of the comment
        io=None
        for o in plio.d_io(self.investments.id):
            if o["id"]==self.id:
                io=o
        
        if self.investments.daily_adjustment is True: #Because it uses adjustment information
            return
        
        comment=Comment().encode(eComment.InvestmentOperation, self)
        if self.operationstypes.id==eOperationType.SharesPurchase:#Compra Acciones
            c=Accountsoperations()
            c.datetime=self.datetime
            c.concepts=Concepts.objects.get(pk=eConcept.BuyShares)
            c.amount=-io['net_account']
            c.comment=comment
            c.accounts=self.investments.accounts
            c.save()
        elif self.operationstypes.id==eOperationType.SharesSale:#// Venta Acciones
            c=Accountsoperations()
            c.datetime=self.datetime
            c.concepts=Concepts.objects.get(pk=eConcept.SellShares)
            c.amount=io['net_account']
            c.comment=comment
            c.accounts=self.investments.accounts
            c.save()
        elif self.operationstypes.id==eOperationType.SharesAdd:#Added
            if(self.commission!=0):
                c=Accountsoperations()
                c.datetime=self.datetime
                c.concepts=Concepts.objects.get(pk=eConcept.BankCommissions)
                c.amount=-io['taxes_account']-io['commission_account']
                c.comment=comment
                c.accounts=self.investments.accounts
                c.save()

    
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
        if self.shares>0 and self.price>self.investments.products.quote_last().quote:
            return True
        elif  self.shares<0 and self.price<self.investments.products.quote_last().quote:
            return True
        return False



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
    currency = models.TextField(blank=True, null=True)
    productstypes = models.ForeignKey('Productstypes', models.DO_NOTHING, blank=True, null=True)
    agrupations = models.TextField(blank=True, null=True)
    web = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    mail = models.TextField(blank=True, null=True)
    percentage = models.IntegerField(blank=False, null=False)
    pci = models.CharField(choices=PCI_CHOICES, max_length=1)
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
    def hurl(request, id):
        return request.build_absolute_uri(reverse('products-detail', args=(id, )))

    def fullName(self):
        return "{} ({})".format(self.name, _(self.stockmarkets.name))
        
        
    def quote_last(self):
        """
            Returns an object
        """
        if hasattr(self, "_quote_last") is False:
            self._quote_last=Quotes.get_quote(self.id, timezone.now())
        return self._quote_last
        
    def quote_penultimate(self):
        """
            Returns an object
        """
        if self.quote_last() is None:
            return None
        if hasattr(self, "_quote_penultimate") is False:
            dt_penultimate=dtaware_day_end_from_date(self.quote_last().datetime.date()-timedelta(days=1), 'UTC')#Better utc to assure
            self._quote_penultimate=Quotes.get_quote(self.id, dt_penultimate)
        return self._quote_penultimate
        

    def quote_lastyear(self):
        """
            Returns an object
        """
        if self.quote_last() is None:
            return None
        if hasattr(self, "_quote_lastyear") is False:
            dt_lastyear=dtaware_year_end(self.quote_last().datetime.year-1, 'UTC')
            self._quote_lastyear=Quotes.get_quote(self.id, dt_lastyear)
        return self._quote_lastyear
        

    def basic_results(self):
        r={
            "id":self.id, 
            "last_datetime":None, 
            "last": None, 
            "penultimate_datetime": None, 
            "penultimate": None, 
            "lastyear_datetime": None, 
            "lastyear": None, 
        }
        if self.quote_last() is not None:
            r["last_datetime"]=self.quote_last().datetime
            r["last"]=self.quote_last().quote
            if self.quote_penultimate() is not None:
                r["penultimate_datetime"]=self.quote_penultimate().datetime
                r["penultimate"]=self.quote_penultimate().quote
                if self.quote_lastyear() is not None:
                    r["lastyear_datetime"]=self.quote_lastyear().datetime
                    r["lastyear"]=self.quote_lastyear().quote
        return r
        
        
    @staticmethod
    def basic_results_from_products_id(products_id):
        """
            Sometimes I only hava an id. PL Investments OPerations
        """
        dt= timezone.now()
        r={
            "id":products_id, 
            "last_datetime":None, 
            "last": None, 
            "penultimate_datetime": None, 
            "penultimate": None, 
            "lastyear_datetime": None, 
            "lastyear": None, 
        }
        quote_last=Quotes.get_quote(products_id, dt)
        if quote_last is not None:
            r["last_datetime"]=quote_last.datetime
            r["last"]=quote_last.quote
            dt_penultimate=dtaware_day_end_from_date(quote_last.datetime.date()-timedelta(days=1), 'UTC')#Better utc to assure
            quote_penultimate=Quotes.get_quote(products_id, dt_penultimate)
            if quote_penultimate is not None:
                r["penultimate_datetime"]=quote_penultimate.datetime
                r["penultimate"]=quote_penultimate.quote
                dt_lastyear=dtaware_year_end(dt.year-1, 'UTC')
                quote_lastyear=Quotes.get_quote(products_id, dt_lastyear)
                if quote_lastyear is not None:
                    r["lastyear_datetime"]=quote_lastyear.datetime
                    r["lastyear"]=quote_lastyear.quote
        return r
        
    ## IBEXA es x2 pero esta en el pricio
    ## CFD DAX no está en el precio
    def real_leveraged_multiplier(self):
        if self.productstypes.id in (eProductType.CFD, eProductType.Future):
            return self.leverages.multiplier
        return 1
        
    def ohclMonthlyBeforeSplits(self):
        if hasattr(self, "_ohcl_monthly_before_splits") is False:
            self._ohcl_monthly_before_splits=cursor_rows("""select 
                t.products_id,
                date_part('year',date) as year, 
                date_part('month', date) as month, 
                (array_agg(t.open order by date))[1] as open, 
                min(t.low) as low, 
                max(t.high) as high, 
                (array_agg(t.close order by date desc))[1] as close 
            from (
            
            select 
                quotes.products_id, 
                datetime::date as date, 
                (array_agg(quote order by datetime))[1] as open, 
                min(quote) as low, 
                max(quote) as high, 
                (array_agg(quote order by datetime desc))[1] as close 
            from quotes 
            where quotes.products_id=%s
            group by quotes.products_id, datetime::date 
            order by datetime::date
            
            
            ) as t
            group by t.products_id,  year, month 
            order by year, month""", (self.id, ))
        return self._ohcl_monthly_before_splits

    def ohclDailyBeforeSplits(self):
        if hasattr(self, "_ohcl_daily_before_splits") is False:
            self._ohcl_daily_before_splits=cursor_rows("""select 
                quotes.products_id, 
                datetime::date as date, 
                (array_agg(quote order by datetime))[1] as open, 
                min(quote) as low, 
                max(quote) as high, 
                (array_agg(quote order by datetime desc))[1] as close 
            from quotes 
            where quotes.products_id=%s
            group by quotes.products_id, datetime::date 
            order by datetime::date """, (self.id, ))
        return self._ohcl_daily_before_splits
        
    @staticmethod
    def next_system_products_id():
        return Products.objects.filter(id__lt=10000000).order_by("-id")[0].id+1

        
    def next_personal_products_id(self):
        return

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

class Quotes(models.Model):
    datetime = models.DateTimeField(blank=True, null=True)
    quote = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    products = models.ForeignKey(Products, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'quotes'
        
    def __str__(self):
        return f"Quote ({self.id}) of '{self.products.name}' at {self.datetime} is {self.quote}"
        
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
    def currency_factor(datetime_, from_, to_ ):
        """
            Gets the factor to pass a currency to other in a datetime
            Returns and object or None
        """
        if from_==to_:
            return 1
            
        if from_== 'EUR' and to_== 'USD':
            q=Quotes.get_quote(74747, datetime_)
            if q is None:
                return None
            else:
                return q.quote    
        if from_== 'USD' and to_== 'EUR':
            q=Quotes.get_quote(74747, datetime_)
            if q is None:
                return None
            else:
                if q.quote==0:
                    return None
                else:
                    return 1/q.quote
        print("NOT FOUND")
        return None


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
    PairsInSameAccount = 1, _('Pairs in same account') #additional {"worse":_, "better":_ "account" }
    Ranges = 2,  _('Product ranges')
    Generic = 3, _('Generic') #additional { }

class Strategies(models.Model):
    name = models.TextField()
    investments = models.TextField(blank=False, null=False)
    dt_from = models.DateTimeField(blank=True, null=True)
    dt_to = models.DateTimeField(blank=True, null=True)
    type = models.IntegerField(choices=StrategiesTypes.choices)
    comment = models.TextField(blank=True, null=True)
    additional1 = models.IntegerField(blank=True, null=True)   
    additional2 = models.IntegerField(blank=True, null=True)   
    additional3 = models.IntegerField(blank=True, null=True)   
    additional4 = models.IntegerField(blank=True, null=True)   
    additional5 = models.IntegerField(blank=True, null=True)   
    additional6 = models.IntegerField(blank=True, null=True)   
    additional7 = models.IntegerField(blank=True, null=True)   
    additional8 = models.IntegerField(blank=True, null=True)   
    additional9 = models.IntegerField(blank=True, null=True)   
    additional10 = models.IntegerField(blank=True, null=True)   
    
    class Meta:
        managed = True
        db_table = 'strategies'
        ordering = ['name']
        
    ## Returns a list with investments ids, due to self.investments is a text string
    def investments_ids(self):
        return string2list_of_integers(self.investments)
        
    ## Returns a queryset with the investments of the strategy, due to self.investments is a text strings
    def investments_queryset(self):
        if hasattr(self, "_investments_queryset") is False:
            self._investments_queryset=Investments.objects.filter(id__in=self.investments_ids()).select_related("products")
        return self._investments_queryset
        
    def investments_urls(self, request):
        r=[]
        for id in self.investments_ids():
            r.append(request.build_absolute_uri(reverse('strategies-detail', args=(id, ))))
        return r


    ## Replaces None for dt_to and sets a very big datetine
    def dt_to_for_comparations(self):
        if self.dt_to is None:
            return timezone.now().replace(hour=23, minute=59)#End of the current day if strategy is not closed
        return self.dt_to




## Class who controls all comments from accountsoperations, investmentsoperations ...
class Comment:
    def __init__(self):
        pass

    ##Obtiene el codigo de un comment
    def getCode(self, string):
        (code, args)=self.get(string)
        return code        

    def getArgs(self, string):
        """
            Obtiene los argumentos enteros de un comment
        """
        (code, args)=self.get(string)
        return args

    def get(self, string):
        """Returns (code,args)"""
        string=string
        try:
            number=string2list_of_integers(string, separator=",")
            if len(number)==1:
                code=number[0]
                args=[]
            else:
                code=number[0]
                args=number[1:]
            return(code, args)
        except:
            return(None, None)
            
    ## Function to generate a encoded comment using distinct parameters
    ## Encode parameters can be:
    ## - eComment.DerivativeManagement, hlcontract
    ## - eComment.Dividend, dividend
    ## - eComment.AccountTransferOrigin operaccountorigin, operaccountdestiny, operaccountorigincommission
    ## - eComment.AccountTransferOriginCommission operaccountorigin, operaccountdestiny, operaccountorigincommission
    ## - eComment.AccountTransferDestiny operaccountorigin, operaccountdestiny, operaccountorigincommission
    ## - eComment.CreditCardBilling creditcard, operaccount
    ## - eComment.CreditCardRefund opercreditcardtorefund
    def encode(self, ecomment, *args):
        if ecomment==eComment.InvestmentOperation:
            return "{},{}".format(eComment.InvestmentOperation, args[0].id)
        elif ecomment==eComment.Dividend:
            return "{},{}".format(eComment.Dividend, args[0].id)        
        elif ecomment==eComment.AccountTransferOrigin:
            operaccountorigincommission_id=-1 if args[2]==None else args[2].id
            return "{},{},{},{}".format(eComment.AccountTransferOrigin, args[0].id, args[1].id, operaccountorigincommission_id)
        elif ecomment==eComment.AccountTransferOriginCommission:
            operaccountorigincommission_id=-1 if args[2]==None else args[2].id
            return "{},{},{},{}".format(eComment.AccountTransferOriginCommission, args[0].id, args[1].id, operaccountorigincommission_id)
        elif ecomment==eComment.AccountTransferDestiny:
            operaccountorigincommission_id=-1 if args[2]==None else args[2].id
            return "{},{},{},{}".format(eComment.AccountTransferDestiny, args[0].id, args[1].id, operaccountorigincommission_id)
        elif ecomment==eComment.CreditCardBilling:
            return "{},{},{}".format(eComment.CreditCardBilling, args[0].id, args[1].id)      
        elif ecomment==eComment.CreditCardRefund:
            return "{},{}".format(eComment.CreditCardRefund, args[0].id)        
    
    def validateLength(self, number, code, args):
        if number!=len(args):
            print("Comment {} has not enough parameters".format(code))
            return False
        return True

    def decode(self, string):
            if string=="":
                return ""
#        try:
            (code, args)=self.get(string)
            if code==None:
                return string

            if code==eComment.InvestmentOperation:
                io=self.decode_objects(string)
#                if io.investments.hasSameAccountCurrency():
                return _("{}: {} shares. Amount: {}. Comission: {}. Taxes: {}").format(io.investments.name, io.shares, io.shares*io.price,  io.commission, io.taxes)
#                else:
#                    return _("{}: {} shares. Amount: {} ({}). Comission: {} ({}). Taxes: {} ({})").format(io.investment.name, io.shares, io.gross(eMoneyCurrency.Product), io.gross(eMoneyCurrency.Account),  io.money_commission(eMoneyCurrency.Product), io.money_commission(eMoneyCurrency.Account),  io.taxes(eMoneyCurrency.Product), io.taxes(eMoneyCurrency.Account))

            elif code==eComment.AccountTransferOrigin:#Operaccount transfer origin
                if not self.validateLength(3, code, args): return string
                aod=Accountsoperations.objects.get(pk=args[1])
                return _("Transfer to {}").format(aod.accounts.name)

            elif code==eComment.AccountTransferDestiny:#Operaccount transfer destiny
            
                if not self.validateLength(3, code, args): return string
                aoo=Accountsoperations.objects.get(pk=args[0])
                return _("Transfer received from {}").format(aoo.accounts.name)

            elif code==eComment.AccountTransferOriginCommission:#Operaccount transfer origin commission
                if not self.validateLength(3, code, args): return string
                
                try:
                    aoo=Accountsoperations.objects.get(pk=args[0])
                    aod=Accountsoperations.objects.get(pk=args[1])
                    return _("Commission transfering {} from {} to {}").format(Currency(aoo.amount, aoo.accounts.currency), aoo.accounts.name, aod.accounts.name)
                except:
                    return _("Commission transfering error")

            elif code==eComment.Dividend:#Comentario de cuenta asociada al dividendo
                dividend=self.decode_objects(string)
                if dividend is not None:
                    return _( "From {}. Gross {}. Net {}.".format(dividend.investments.name, Currency(dividend.gross,  dividend.investments.accounts.currency), Currency(dividend.net, dividend.investments.accounts.currency)))
                return _("Error decoding dividend comment")

            elif code==eComment.CreditCardBilling:#Facturaci´on de tarjeta diferida
                d=self.decode_objects(string)
                if d["creditcard"] is not None:
                    number=cursor_one_field("select count(*) from creditcardsoperations where accountsoperations_id=%s", (d["operaccount"].id, ))
                    return _("Billing {} movements of {}").format(number, d["creditcard"].name)
                return _("Error decoding credit card billing comment")

            elif code==eComment.CreditCardRefund:#Devolución de tarjeta
                if not self.validateLength(1, code, args): return string
                cco=Creditcardsoperations.objects.get(pk=args[0])
                money=Currency(cco.amount, cco.creditcards.accounts.currency)
                return _("Refund of {} payment of which had an amount of {}").format(dtaware2string(cco.datetime), money)
#        except:
#            return _("Error decoding comment {}").format(string)

    def decode_objects(self, string):
            (code, args)=self.get(string)
            if code==None:
                return None

            if code==eComment.InvestmentOperation:
                if not self.validateLength(1, code, args): return None
                io=Investmentsoperations.objects.select_related("investments").get(pk=args[0])
                return io

            elif code in (eComment.AccountTransferOrigin,  eComment.AccountTransferDestiny, eComment.AccountTransferOriginCommission):
                if not self.validateLength(3, code, args): return None
                aoo=Accountsoperations.objects.get(pk=args[0])
                aod=Accountsoperations.objects.get(pk=args[1])
                if args[2]==-1:
                    aoc=None
                else:
                    aoc=Accountsoperations.objects.get(pk=args[2])
                return {"origin":aoo, "destiny":aod, "commission":aoc }

            elif code==eComment.Dividend:#Comentario de cuenta asociada al dividendo
                if not self.validateLength(1, code, args): return None
                try:
                    return Dividends.objects.get(pk=args[0])
                except:
                    return None

            elif code==eComment.CreditCardBilling:#Facturaci´on de tarjeta diferida
                if not self.validateLength(2, code, args): return string
                creditcard=Creditcards.objects.get(pk=args[0])
                operaccount=Accountsoperations.objects.get(pk=args[1])
                return {"creditcard":creditcard, "operaccount":operaccount}

            elif code==eComment.CreditCardRefund:#Devolución de tarjeta
                if not self.validateLength(1, code, args): return string
                cco=Creditcardsoperations.objects.get(pk=args[0])
                money=Currency(cco.amount, cco.creditcards.accounts.currency)
                return _("Refund of {} payment of which had an amount of {}").format(dtaware2string(cco.datetime), money)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    favorites= models.ManyToManyField(Products)
    currency=models.CharField(max_length=4, blank=False, null=False, default="EUR")
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

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.id is None and EstimationsDps.objects.filter(year=self.year, products=self.products).exists(): 
            old=EstimationsDps.objects.get(year=self.year, products=self.products)
            self.id=old.id #To update it
            print("Updated estimation dps")
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
    def lod_ym_balance_user_by_operationstypes(request, operationstypes_id, year=None):
        """
            Returns a list of rows with a structure as in lod_ymv.lod_ymv_transposition
            if year only shows this year, else all database registers
        """
            
        ld=[]
        for currency in Accounts.currencies():
            ao=Accountsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, accounts__currency=currency)
            
            if year is not None:
                ao=ao.filter(datetime__year=year)
            
            ao=ao.values("datetime__year","datetime__month").annotate(Sum("amount")).order_by("datetime__year", "datetime__month")
            for o in  ao:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})

            cc=Creditcardsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, creditcards__accounts__currency=currency)
            if year is not None:
                cc=cc.filter(datetime__year=year)
            cc=cc.values("datetime__year","datetime__month").annotate(Sum("amount")) 
            for o in  cc:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})
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
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})

            cc=Creditcardsoperations.objects.filter(concepts__id__in=concepts_ids, creditcards__accounts__currency=currency)
            if year is not None:
                cc=cc.filter(datetime__year=year)
            cc=cc.values("datetime__year","datetime__month").annotate(Sum("amount")) 
            for o in  cc:
                ld.append({"year":o["datetime__year"], "month":o["datetime__month"], "value": Assets.money_convert(dtaware_month_end(o["datetime__year"], o["datetime__month"], request.user.profile.zone), o["amount__sum"], currency, request.user.profile.currency)})
        return lod_ymv.lod_ymv_transposition(ld)

    @staticmethod
    def money_convert(dt, amount, from_,  to_):   
        if from_==to_:
            return amount
        return cursor_one_field("select * from money_convert(%s, %s, %s, %s)", (dt, amount, from_,  to_))
        
    @staticmethod
    def pl_total_balance(dt, local_currency):
        """
            Returns a dict with the following keys:
            {'accounts_user': 0, 'investments_user': 0, 'total_user': 0, 'investments_invested_user': 0}
        """
        return loads(cursor_rows("select * from pl_total_balance(%s,%s)", (dt, local_currency, ))[0]["pl_total_balance"], object_hook=loads_hooks_tb)[0]

    @staticmethod
    def pl_investment_operations(dt, local_currency, list_ids, mode):
        """
            If list_ids is None returns investment_operations for all investments
            Returns a dict with the following keys:
        """
        return loads(cursor_rows("select * from pl_investment_operations(%s,%s,%s,%s)", (dt, local_currency, list_ids, mode))[0]["pl_investment_operations"], object_hook=loads_hooks_io)


class PlInvestmentOperations():
    """
        Class to operate with Assets.pl_investment_operations result
    """
    def __init__(self, t):
        self._t=t
    
    @classmethod
    def from_qs(cls, dt,  local_currency,  qs_investments,  mode):
        ids=list(qs_investments.values_list('pk',flat=True))
        return cls.from_ids(dt, local_currency, ids, mode)

    @classmethod
    def from_ids(cls, dt,  local_currency,  list_ids,  mode):
        plio=Assets.pl_investment_operations(dt, local_currency, list_ids, mode)
        return cls(plio)


    @classmethod
    def from_all(cls, dt,  local_currency,  mode):
        plio=Assets.pl_investment_operations(dt, local_currency, None, mode)
        return cls(plio)
        
    @staticmethod
    def qs_investments_to_lod(qs):
        """
            Converts a qs to a lod investments used in moneymoney_pl
        """
        r=[]
        for i in qs:
            r.append({
                "products_id": i.products.id, 
                "investments_id": str(i.id), 
                "multiplier": i.products.leverages.multiplier, 
                "currency_account": i.accounts.currency, 
                "currency_product": i.products.currency, 
                "productstypes_id": i.products.productstypes.id, 
            })
        return r        
    @staticmethod
    def list_unsaved_io_to_lod(list_):
        """
            Converts a list of unsaved investmentsoperations to a lod_ios used in moneymoney_pl
        """
        r=[]
        for i, io in enumerate(list_):
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "investments_id": str(i.investments.id), 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "comment": io.comment, 
                "currency_conversion":io.currency_conversion
            })
        return r
        
    @staticmethod
    def qs_investments_to_lod_ios(qs):
        """
            Converts a list of unsaved investmentsoperations to a lod_ios used in moneymoney_pl
        """
        r=[]
        ids=tuple(qs.values_list('pk',flat=True))
        for i, io in enumerate(Investmentsoperations.objects.filter(investments_id__in=ids).order_by("datetime")):
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "investments_id": str(io.investments.id), 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "comment": io.comment, 
                "currency_conversion":io.currency_conversion
            })
        return r
    @staticmethod
    def external_query_factors_quotes(t):
                
        # Get quotes and factors
        for products_id, dt in t["lazy_quotes"].keys():
            quote=cursor_rows("select quote from quote(%s, %s)", (products_id, dt))[0]['quote']
            t["lazy_quotes"][(products_id,dt)]=quote if quote is not None else 0

        for from_,  to_, dt in t["lazy_factors"].keys():
            factor=cursor_rows("SELECT * FROM currency_factor(%s,%s,%s)", [dt, from_, to_])[0]['currency_factor']
            t["lazy_factors"][(from_, to_, dt)]=factor if factor is not None else 0

    @classmethod
    def plio_id_from_virtual_investments_simulation(cls, dt,  local_currency,  lod_investment_data, lod_ios_to_simulate, mode):
        """
        Devuelve un plio_Id, solo se debe pasar una inversión
        
        investments_id canbe virtual  coordinated with data and ios_to_simulate
        lod_ios_to_simulate must load all io and simulation ios
        
        Lod_investments_data
        [{'products_id': -81742, 'invesments_id': '445', 'multiplier': Decimal('2'), 'currency_account': 'EUR', 'currency_product': 'EUR', 'productstypes_id': 4}]

        Class method lod_simulated_ios must have
            r.append({
                "id":-i, 
                "operationstypes_id": io.operationstypes.id, 
                "shares": io.shares, 
                "taxes": io.taxes, 
                "commission": io.commission, 
                "price": io.price, 
                "datetime": io.datetime, 
                "currency_conversion":io.currency_conversion
                 "investments_id": virtual_investments_id, 
            })
        """
        lod_ios_to_simulate= sorted(lod_ios_to_simulate,  key=lambda item: item['datetime'])
        t=calculate_ios_lazy(dt, lod_investment_data, lod_ios_to_simulate, local_currency)
        cls.external_query_factors_quotes(t)
        t=calculate_ios_finish(t, mode)
        return cls(t).d(lod_investment_data[0]["investments_id"])
        
        
    @classmethod
    def plio_id_from_strategy(cls, dt,  local_currency,  strategy):
        """
            Returns a plio_id adding all io, io_current,io_historical of all investments (plio) and returning only one plio. Only adds, do not calculate
        """
        
        plio=cls.from_ids(dt, local_currency, strategy.investments_ids(), 1)
        
        r={}
        r["data"]={}
        r["data"]["products_id"]="HETEROGENEOUS"
        r["data"]["investments_id"]=strategy.investments_ids()
        r["data"]["multiplier"]="HETEROGENEOUS"
        r["data"]["currency_product"]="HETEROGENEOUS"
        r["data"]["productstypes_id"]="HETEROGENEOUS"
        r["data"]["currency_user"]=local_currency
        
        r["io"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io(plio_id):
                if strategy.dt_from<=o["datetime"] and o["datetime"]<=strategy.dt_to_for_comparations():
                    r["io"].append(o)
        r["io"]= sorted(r["io"],  key=lambda item: item['datetime'])

        r["io_current"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io_current(plio_id):
                if strategy.dt_from<=o["datetime"] and o["datetime"]<=strategy.dt_to_for_comparations():
                    r["io_current"].append(o)
        r["io_current"]= sorted(r["io_current"],  key=lambda item: item['datetime'])
                
        r["total_io_current"]={}
        r["total_io_current"]["balance_user"]=lod.lod_sum(r["io_current"], "balance_user")
        r["total_io_current"]["balance_investment"]="HETEROGENEOUS"
        r["total_io_current"]["balance_futures_user"]=lod.lod_sum(r["io_current"], "balance_futures_user")
        r["total_io_current"]["gains_gross_user"]=lod.lod_sum(r["io_current"], "gains_gross_user")
        r["total_io_current"]["gains_net_user"]=lod.lod_sum(r["io_current"], "gains_net_user")
        r["total_io_current"]["shares"]=lod.lod_sum(r["io_current"], "shares")
        r["total_io_current"]["invested_user"]=lod.lod_sum(r["io_current"], "invested_user")
        r["total_io_current"]["invested_investment"]="HETEROGENEOUS"
        
        r["io_historical"]=[]
        for plio_id in plio.list_investments_id():
            for o in plio.d_io_historical(plio_id):
                if strategy.dt_from<=o["dt_end"] and o["dt_end"]<=strategy.dt_to_for_comparations():
                    r["io_historical"].append(o)
        r["io_historical"]= sorted(r["io_historical"],  key=lambda item: item['dt_end'])

        r["total_io_historical"]={}
        r["total_io_historical"]["gains_net_user"]=lod.lod_sum(r["total_io_historical"], "gains_net_user")
        return r

        
    @classmethod
    def from_merging_io_current(cls, dt,  local_currency,  qs_investments, mode):
        """
            Return a plio merging in same virtual (negative) id all investments in qs with same product
            only io_current and io_historical
        """
        def get_investments_id(product):
            """
                Function Returns a list of integers with all investments_id of a product in plio
            """
            r=[]
            for id in plio.list_investments_id():
                if product.id==plio.d_data(id)["products_id"]:
                    r.append(int(id))
            return r
        
        
        ###############
        plio=cls.from_qs(dt, local_currency, qs_investments, mode)
        products_ids=list(Investments.objects.filter(active=True).values_list("products__id",  flat=True).distinct())
        t_merged={}
        for product in Products.objects.filter(id__in=products_ids):
            t_merged[str(product.id)]={}
            t_merged[str(product.id)]["data"]={}
            t_merged[str(product.id)]["data"]["products_id"]=product.id
            t_merged[str(product.id)]["data"]["investments_id"]=get_investments_id(product)
            t_merged[str(product.id)]["data"]["multiplier"]=product.leverages.multiplier
            t_merged[str(product.id)]["data"]["currency_product"]=product.currency
            t_merged[str(product.id)]["data"]["productstypes_id"]=product.productstypes.id
            t_merged[str(product.id)]["data"]["currency_user"]=local_currency
            
            t_merged[str(product.id)]["io_current"]=[]
            for plio_id in plio.list_investments_id():
                if plio.d_data(plio_id)["products_id"]==product.id:
                    for o in plio.d_io_current(plio_id):
                        t_merged[str(product.id)]["io_current"].append(o)
            t_merged[str(product.id)]["io_current"]= sorted(t_merged[str(product.id)]["io_current"],  key=lambda item: item['datetime'])
            
            average_price_investment=0
            
            t_merged[str(product.id)]["total_io_current"]={}
            t_merged[str(product.id)]["total_io_current"]["balance_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_user")
            t_merged[str(product.id)]["total_io_current"]["balance_investment"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_investment")
            t_merged[str(product.id)]["total_io_current"]["balance_futures_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "balance_futures_user")
            t_merged[str(product.id)]["total_io_current"]["gains_gross_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "gains_gross_user")
            t_merged[str(product.id)]["total_io_current"]["gains_net_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "gains_net_user")
            t_merged[str(product.id)]["total_io_current"]["shares"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "shares")
            t_merged[str(product.id)]["total_io_current"]["invested_user"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "invested_user")
            t_merged[str(product.id)]["total_io_current"]["invested_investment"]=lod.lod_sum(t_merged[str(product.id)]["io_current"], "invested_investment")
            t_merged[str(product.id)]["total_io_current"]["balance_user"]=average_price_investment
            
            t_merged[str(product.id)]["io_historical"]=[]
            for plio_id in plio.list_investments_id():
                if plio.d_data(plio_id)["products_id"]==product.id:
                    for o in plio.d_io_historical(plio_id):
                        t_merged[str(product.id)]["io_historical"].append(o)
            t_merged[str(product.id)]["io_historical"]= sorted(t_merged[str(product.id)]["io_historical"],  key=lambda item: item['dt_end'])

            t_merged[str(product.id)]["total_io_historical"]={}
            t_merged[str(product.id)]["total_io_historical"]["gains_net_user"]=lod.lod_sum(t_merged[str(product.id)]["total_io_historical"], "gains_net_user")
            #t_merged[str(product.id)]["total_io_historical"]["commission_account"]=lod.lod_sum(t_merged[str(product.id)]["total_io_historical"], "commission_account")

        return cls(t_merged)
        
    def basic_results(self, id):
        """
        Public method Id is investments id
        """
        if not "basic_results" in self._t:
            self._t["basic_results"]={}
            
        products_id=str(self.d_data(str(id))["products_id"])
        if not products_id in self._t["basic_results"]:
            self._t["basic_results"][products_id]=Products.basic_results_from_products_id(products_id)
        return self._t["basic_results"][products_id]
        
    def ioc_percentage_annual_user(self, ioc):
        """
        Public method ioc is a io_current dictionary
        """
        if ioc["datetime"].year==date.today().year:
            lastyear=ioc["price_user"] #Product value, self.money_price(type) not needed.
        else:
            lastyear=self.basic_results(ioc["investments_id"])["lastyear"]
        if self.basic_results(ioc["investments_id"])["lastyear"] is None or lastyear is None:
            return Percentage()

        if ioc["shares"]>0:
            return Percentage(self.basic_results(ioc["investments_id"])["last"]-Decimal(lastyear), lastyear)
        else:
            return Percentage(-(self.basic_results(ioc["investments_id"])["last"]-Decimal(lastyear)), lastyear)

    def ioc_percentage_sellingpoint(self, ioc, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.basic_results(ioc["investments_id"])["last"], selling_price)

    def total_io_current_percentage_total_user(self, id):
        if self.d_total_io_current(id)["invested_user"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(self.d_total_io_current(id)['gains_gross_user'], self.d_total_io_current(id)["invested_user"])
        
    def total_io_current_percentage_sellingpoint(self, id, selling_price):
        if selling_price is None or selling_price==0:
            return Percentage()
        return percentage_between(self.basic_results(id)["last"], selling_price)
        
    def ioc_days(self, ioc):
            return (date.today()-ioc["datetime"].date()).days
    def ioh_years(self, ioh):
        return round(Decimal((ioh["dt_end"]-ioh["dt_start"]).days/365), 2)

    def ioc_percentage_apr_user(self, ioc):
            dias=self.ioc_days(ioc)
            if dias==0:
                dias=1
            return Percentage(self.ioc_percentage_total_user(ioc)*365,  dias)

    def ioc_percentage_total_user(self, ioc):
        """
            Returns total porcentage of an current investment operation dictionary
        """
        if ioc["invested_user"] is None:#initiating xulpymoney
            return Percentage()
        return Percentage(ioc['gains_gross_user'], ioc["invested_user"])
        
    def mode(self):
        return self._t["mode"]
        
    def list_investments_id(self):
        r=[]
        for key in self.keys():
            if key not in t_keys_not_investment():
                r.append(key)
        return r
        
    def qs_investments(self):
        return Investments.objects.filter(id__in = self.list_investments_id()).select_related("accounts")
        
    def d(self, id_):
        return self._t[str(id_)]
        
    def t(self):
        return self._t
        
    def keys(self):
        return list(self._t.keys())
    def d_data(self, id_):
        return self._t[str(id_)]["data"]
    def d_io(self, id_):
        return self._t[str(id_)]["io"]
    def d_io_current(self, id_):
        return self._t[str(id_)]["io_current"]
    def d_io_historical(self, id_):
        return self._t[str(id_)]["io_historical"]
    def d_total_io(self, id_):
        return self._t[str(id_)]["total_io"]
    def d_total_io_current(self, id_):
        return self._t[str(id_)]["total_io_current"]
    def d_total_io_historical(self, id_):
        return self._t[str(id_)]["total_io_historical"]
    def sum_total_io_current(self):
        return self._t["sum_total_io_current"]
    def sum_total_io_historical(self):
        return self._t["sum_total_io_historical"]
        
    def investment(self, id_):
        return Investments.objects.get(pk=id_)
        
    def dumps(self):
        return dumps(self._t,  indent=4,  cls=MyDjangoJSONEncoder )
        
    def print(self):
        print(self.dumps())
        
    def io_historical_sum_between_dt(self, dt_from, dt_to,  key, productstypes_id=None):
        r=0
        for investments_id in self.list_investments_id():
            for ioh in self.d_io_historical(investments_id):
                if dt_from <= ioh["dt_end"] and ioh["dt_end"]<=dt_to:
                    if productstypes_id is None:
                        r=r+ioh[key]
                    else:
                        if int(self.d_data(investments_id)["productstypes_id"])==int(productstypes_id):
                            r=r+ioh[key]
        return r

    def io_sum_between_dt(self, dt_from, dt_to, key):
        r=0
        for investments_id in self.list_investments_id():
            for o in self.d_io(investments_id):
                if dt_from<=o["datetime"] and o["datetime"]<=dt_to:
                    r=r - o[key]
        return r

    def io_current_highest_price(self):
        """
        Public method Returns highest io operation price of all io operations
        """
        
        r=0
        for investments_id in self.list_investments_id():
            for o in self.d_io_current(investments_id):
                if o["price_investment"]>r:
                    r=o["price_investment"]
        return r
    def io_current_lowest_price(self):
        """
        Public method Returns highest io operation price of all io operations
        """
        
        r=10000000
        for investments_id in self.list_investments_id():
            for o in self.d_io_current(investments_id):
                if o["price_investment"]<r:
                    r=o["price_investment"]
        return r

    def  io_current_last_operation_excluding_additions(self, id):
        """
            Returns last investment operation excluding additions
        """
        for o in reversed(self.d_io_current(id)):
            if o["operationstypes_id"]!=6:# Shares Additions
                return o
        return None

class FastOperationsCoverage(models.Model):
    datetime = models.DateTimeField(blank=False, null=False)
    investments = models.ForeignKey('Investments', models.DO_NOTHING, blank=False, null=False)
    amount= models.DecimalField(max_digits=30, decimal_places=6, blank=False, null=False)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        
        

def request_get(absolute_url, user_token):
    ## verify should be changed
    a=get(absolute_url, headers={'Authorization': f'Token {user_token}'}, verify=False)
    print(a.content)
    return loads(a.content)

