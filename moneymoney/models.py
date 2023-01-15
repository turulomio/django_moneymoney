from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Case, When
from django.db.models.expressions import RawSQL
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils import timezone
from moneymoney.types import eComment, eConcept, eProductType, eOperationType
from moneymoney.investmentsoperations import InvestmentsOperations
from moneymoney.reusing.casts import string2list_of_integers
from moneymoney.reusing.connection_dj import cursor_one_field, cursor_one_column, cursor_one_row, cursor_rows, execute
from moneymoney.reusing.currency import Currency, currency_symbol
from moneymoney.reusing.datetime_functions import dtaware_month_end, dtaware, dtaware2string

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
    def balance(self, dt,  local_currency):
        r=cursor_one_row("select * from account_balance(%s,%s,%s)", (self.id, dt, local_currency))
        return r['balance_account_currency'], r['balance_user_currency']
            
            
    @staticmethod
    def balance_user_currency(qs, dt):
        if len (qs)==0:
            return 0
            
        ids=tuple(qs.values_list("id",  flat=True).distinct())
        return cursor_one_field("select sum((account_balance(accounts.id,%s,'EUR')).balance_user_currency) from  accounts where id in %s", (dt, ids))

            
    @staticmethod
    def currencies():
        """
        Returns a list with distinct currencies in accounts

        @return DESCRIPTION
        @rtype TYPE
        """
        return cursor_one_column("select distinct(currency) from accounts")

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
            self._balance_accounts=Accounts.balance_user_currency(qs,  timezone.now())
        return self._balance_accounts

    def balance_investments(self, request):
        from moneymoney.investmentsoperations import InvestmentsOperationsTotalsManager
        if hasattr(self, "_balance_investments") is False:
            iotm=InvestmentsOperationsTotalsManager.from_investment_queryset(self.investments(active=True), timezone.now(), request)
            self._balance_investments=iotm.current_balance_user()
        return self._balance_investments
        
    def balance_total(self, request):
        return self.balance_accounts()+self.balance_investments(request)

    def investments(self, active):
        investments= Investments.objects.all().select_related("products").select_related("products__productstypes").select_related("accounts").filter(accounts__banks__id=self.id, active=active)
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
    accountsoperations = models.ForeignKey('Accountsoperations', models.DO_NOTHING, null=True)
    commission = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    concepts = models.ForeignKey(Concepts, models.DO_NOTHING)
    currency_conversion = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        managed = True
        db_table = 'dividends'

    def delete(self):
        execute("delete from accountsoperations where id=%s",(self.accountsoperations.id, )) 
        models.Model.delete(self)
       
        
    ## TODO This method should take care of diffrent currencies in accounts. Dividens are in account currency
    @staticmethod
    def netgains_dividends(year, month):
        dividends=cursor_one_field("""
    select 
        sum(net) 
    from 
        dividends 
    where 
        date_part('year',datetime)=%s and
        date_part('month',datetime)=%s
    """, (year, month))
        if dividends is None:
            dividends=0
        return dividends

    ## TODO This method should take care of diffrent currencies in accounts. Dividens are in account currency
    @staticmethod
    def net_gains_baduser_between_datetimes_for_some_investments(ids, from_dt,  to_dt):
        dividends=cursor_one_field("""select sum(net) from dividends where datetime>=%s and datetime<=%s  and investments_id in %s""", (from_dt, to_dt, tuple(ids) ))
        if dividends is None:
            dividends=0
        return dividends
        

    ## TODO This method should take care of diffrent currencies in accounts. Dividens are in account currency
    @staticmethod
    def net_gains_baduser_between_datetimes(from_dt,  to_dt):
        dividends=cursor_one_field("""select sum(net) from dividends where datetime>=%s and datetime<=%s""", (from_dt, to_dt ))
        if dividends is None:
            dividends=0
        return dividends

    ## Esta función actualiza la tabla investmentsaccountsoperations que es una tabla donde 
    ## se almacenan las accountsoperations automaticas por las operaciones con investments. Es una tabla 
    ## que se puede actualizar en cualquier momento con esta función
    def update_associated_account_operation(self):
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
        self.save()

class Dps(models.Model):
    date = models.DateField(blank=False, null=False)
    gross = models.DecimalField(max_digits=18, decimal_places=6, blank=False, null=False)
    products = models.ForeignKey('Products', models.DO_NOTHING, blank=False, null=False)
    paydate = models.DateField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'dps'

class Investments(models.Model):
    name = models.TextField()
    active = models.BooleanField()
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    selling_price = models.DecimalField(max_digits=100, decimal_places=6)
    products = models.ForeignKey('Products', models.DO_NOTHING, blank=False, null=False)
    selling_expiration = models.DateField(blank=True, null=True)
    daily_adjustment = models.BooleanField()
    balance_percentage = models.DecimalField(max_digits=18, decimal_places=6)

    class Meta:
        managed = True
        db_table = 'investments'
        ordering = ['name']
        

    def __str__(self):
        return self.fullName()

    def fullName(self):
        return "{} ({})".format(self.name, self.accounts.name)
            
    def operations(self, request, local_currency):
        if hasattr(self, "_operations") is False:
            self._operations=InvestmentsOperations.from_investment(request, self, timezone.now(), local_currency)
        return self._operations

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
        r=cursor_one_field(" select sum(shares) from investmentsoperations where investments_id=%s", (self.id, ))
        if r is None:
            return 0
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
        
class Investmentsoperations(models.Model):
    operationstypes = models.ForeignKey('Operationstypes', models.DO_NOTHING, blank=False, null=False)
    investments = models.ForeignKey(Investments, models.DO_NOTHING, blank=False, null=False)
    shares = models.DecimalField(max_digits=100, decimal_places=6, blank=False, null=False)
    taxes = models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False)
    commission = models.DecimalField(max_digits=100, decimal_places=2, blank=False, null=False)
    price = models.DecimalField(max_digits=100, decimal_places=6, blank=False, null=False)
    datetime = models.DateTimeField(blank=False, null=False)
    comment = models.TextField(blank=True, null=True)
    show_in_ranges = models.BooleanField(blank=False, null=False)
    currency_conversion = models.DecimalField(max_digits=30, decimal_places=10, blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'investmentsoperations'
        
    def __str__(self):
        return "InvestmentOperation"

    @transaction.atomic
    def save(self, *args, **kwargs):
            models.Model.save(self)

    @transaction.atomic
    def delete(self):
#        execute("delete from investmentsaccountsoperations where investmentsoperations_id=%s",(self.id, )) 
        
        concepts=Concepts.objects.filter(pk__in=(eConcept.BuyShares, eConcept.SellShares, eConcept.BankCommissions))
        qs_ao=Accountsoperations.objects.filter(concepts__in=concepts, comment=f'{eComment.InvestmentOperation},{self.id}')
        print(qs_ao)
        qs_ao.delete()
        models.Model.delete(self)
        


    ## Esta función actualiza la tabla investmentsaccountsoperations que es una tabla donde 
    ## se almacenan las accountsoperations automaticas por las operaciones con investments. Es una tabla 
    ## que se puede actualizar en cualquier momento con esta función
    @transaction.atomic
    def update_associated_account_operation(self,  request):
        #/Borra de la tabla investmentsaccountsoperations los de la operinversión pasada como parámetro
        #execute("delete from investmentsaccountsoperations where investmentsoperations_id=%s",(self.id, )) 
        #Selecciona si existe una accountoperation con comment '10000,self.id' con id_concepts 35,29 y 38
        concepts=Concepts.objects.filter(pk__in=(eConcept.BuyShares, eConcept.SellShares, eConcept.BankCommissions))
        qs_ao=Accountsoperations.objects.filter(concepts__in=concepts, comment=f'{eComment.InvestmentOperation},{self.id}')
        print(qs_ao)
        qs_ao.delete()

        investment_operations=InvestmentsOperations.from_investment(request, self.investments, timezone.now(), request.user.profile.currency)
        io=investment_operations.o_find_by_id(self.id)
        
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

class Operationstypes(models.Model):
    name = models.TextField()

    class Meta:
        managed = True
        db_table = 'operationstypes'
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

class Orders(models.Model):
    date = models.DateField()
    expiration = models.DateField()
    shares = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    price = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
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



class Products(models.Model):
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
    decimals = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'products'
        ordering = ['name']

    def __str__(self):
        return self.fullName()

    def fullName(self):
        return "{} ({})".format(self.name, _(self.stockmarkets.name))
        
    def currency_symbol(self):
        return currency_symbol(self.currency)

    def basic_results(self):
        if hasattr(self, "_basic_results") is False:
            self._basic_results=cursor_one_row("select * from last_penultimate_lastyear(%s,%s)", (self.id, timezone.now() ))
        return self._basic_results
        
        
    @staticmethod
    def get_d_product_with_basics(id):
        return cursor_one_row("select * from products,last_penultimate_lastyear(products.id, now()) where products.id=%s", (id, ))
        
    ## IBEXA es x2 pero esta en el pricio
    ## CFD DAX no está en el precio
    def real_leveraged_multiplier(self):
        if self.productstypes.id in (eProductType.CFD, eProductType.Future):
            return self.leverages.multiplier
        return 1
        
    def stockmarket_close_time(self):
        if self.productstypes.id==eProductType.CFD or self.productstypes.id==eProductType.Future:
            return self.stockmarkets.closes_futures
        return self.stockmarkets.closes
    def stockmarket_start_time(self):
        if self.productstypes.id==eProductType.CFD or self.productstypes.id==eProductType.Future:
            return self.stockmarkets.starts_futures
        return self.stockmarkets.starts

    def quote(self, dt):
        return cursor_one_row("select * from quote(%s,%s)", (self.id, dt ))
        
    def ohclMonthlyBeforeSplits(self):
        if hasattr(self, "_ohcl_monthly_before_splits") is False:
            self._ohcl_monthly_before_splits=cursor_rows("select * from ohclmonthlybeforesplits(%s)", (self.id, ))
        return self._ohcl_monthly_before_splits

    def ohclDailyBeforeSplits(self):
        if hasattr(self, "_ohcl_daily_before_splits") is False:
            self._ohcl_daily_before_splits=cursor_rows("select * from ohcldailybeforesplits(%s)", (self.id, ))
        return self._ohcl_daily_before_splits
        
    @staticmethod
    def qs_products_of_investments():
        return Products.objects.filter(id__in=RawSQL('select products.id from products, investments where products.id=investments.products_id', ()))
        
    @staticmethod
    def qs_products_of_active_investments():
        return Products.objects.filter(id__in=RawSQL('select distinct(products.id) from products, investments where products.id=investments.products_id and investments.active is true', ()))


    def highest_investment_operation_price(self):
        return cursor_one_field("""
select 
    max(price) 
from 
    investmentsoperations, 
    investments 
where 
    products_id=%s and 
    investmentsoperations.investments_id=investments.id
""", (self.id, ))    

    def lowest_investment_operation_price(self):
        return cursor_one_field("""
select 
    min(price) 
from 
    investmentsoperations, 
    investments 
where 
    products_id=%s and 
    investmentsoperations.investments_id=investments.id
""", (self.id, ))
        

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
        
    def save(self, *args, **kwargs):
        if self.datetime-timezone.now()>timedelta(days=1):
            return _("Error saving '{0}'. Datetime it's in the future").format(self)
        quotes=Quotes.objects.all().filter(datetime=self.datetime, products=self.products)
        if quotes.count()>0:
            for quote in quotes:
                quote.quote=self.quote
                models.Model.save(quote)
                return _("Updating '{0}'").format(quote)
        else:
            models.Model.save(self)
            return _("Inserting '{0}'").format(self)



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


    
## @return accounts, investments, totals, invested
def total_balance(dt, local_currency):
    return cursor_one_row("select * from total_balance(%s,%s)", (dt, local_currency, ))

def money_convert(dt, amount, from_,  to_):   
    if from_==to_:
        return amount
    return cursor_one_field("select * from money_convert(%s, %s, %s, %s)", (dt, amount, from_,  to_))

## This method should take care of diffrent currenciesç
## @param month can be None to calculate all year
def balance_user_by_operationstypes(year,  month,  operationstypes_id, local_currency, local_zone):
    
    strmonth="" if month is None else "date_part('month',datetime)=%s and "
    
    r=0
    for currency in Accounts.currencies():
        if month is  None:
            parameters=(operationstypes_id, year,  currency, operationstypes_id, year,  currency)
        else:
            parameters=(operationstypes_id, year, month,  currency, operationstypes_id, year, month,  currency)
        for row in cursor_rows(f"""
            select sum(amount) as amount 
            from 
                accountsoperations,
                accounts, 
                concepts
            where 
                concepts.operationstypes_id=%s and 
                date_part('year',datetime)=%s and
                {strmonth}
                accounts.currency=%s and
                accounts.id=accountsoperations.accounts_id    AND
                accountsoperations.concepts_id=concepts.id
        union all 
            select sum(amount) as amount 
            from 
                creditcardsoperations ,
                creditcards,
                accounts, 
                concepts
            where 
                concepts.operationstypes_id=%s and 
                date_part('year',datetime)=%s and
                {strmonth}
                accounts.currency=%s and
                accounts.id=creditcards.accounts_id and
                creditcards.id=creditcardsoperations.creditcards_id   AND
                creditcardsoperations.concepts_id=concepts.id""", parameters):

            if row['amount'] is not None:
                if local_currency==currency:
                    r=r+row['amount']
                else:
                    if month is None:                      
                        r=r+money_convert(dtaware_month_end(year, 12, local_zone), row['amount'], currency, local_currency)
                    else:
                        r=r+money_convert(dtaware_month_end(year, month, local_zone), row['amount'], currency, local_currency)
    return r

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
        db_table = 'estimation_dps'

