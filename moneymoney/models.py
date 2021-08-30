# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from datetime import date, timedelta
from decimal import Decimal
Decimal()#Internal eval

from django.db import models, transaction
from django.db.models import Case, When
from django.db.models.expressions import RawSQL
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.utils import timezone

from moneymoney.reusing.connection_dj import cursor_one_field, cursor_one_column, cursor_one_row, cursor_rows, execute

from moneymoney.investmentsoperations import InvestmentsOperations_from_investment
from moneymoney.reusing.casts import string2list_of_integers
from moneymoney.reusing.currency import Currency, currency_symbol
from moneymoney.reusing.datetime_functions import dtaware_month_end, dtaware, dtaware2string
from moneymoney.reusing.percentage import Percentage

from enum import IntEnum

        
class eProductType(IntEnum):
    """
        IntEnum permite comparar 1 to eProductType.Share
    """
    Share=1
    Fund=2
    Index=3
    ETF=4
    Warrant=5
    Currency=6
    PublicBond=7
    PensionPlan=8
    PrivateBond=9
    Deposit=10
    Account=11
    CFD=12
    Future=13
    
class eOHCLDuration:
    Day=1
    Week=2
    Month=3
    Year=4

## Operation tipes
class eOperationType:
    Expense=1
    Income=2
    Transfer=3
    SharesPurchase=4
    SharesSale=5
    SharesAdd=6
    CreditCardBilling=7
    TransferFunds=8
    TransferSharesOrigin=9
    TransferSharesDestiny=10
    DerivativeManagement=11
    
class eTickerPosition(IntEnum):
    """It's the number to access to a python list,  not to postgresql. In postgres it will be +1"""
    Yahoo=0
    Morningstar=1
    Google=2
    QueFondos=3
    InvestingCom=4
    
    def postgresql(etickerposition):
        return etickerposition.value+1
        
    ## Returns the number of atributes
    def length():
        return 5


class eComment:
    InvestmentOperation=10000
    Dividend=10004
    AccountTransferOrigin=10001
    AccountTransferDestiny=10002
    AccountTransferOriginCommission=10003
    CreditCardBilling=10005
    CreditCardRefund=10006

## System concepts tipified
class eConcept:
    OpenAccount=1
    TransferOrigin=4
    TransferDestiny=5
    TaxesReturn=6
    BuyShares=29
    SellShares=35
    TaxesPayment=37
    BankCommissions=38
    Dividends=39
    CreditCardBilling=40
    AddShares=43
    AssistancePremium=50
    CommissionCustody=59
    DividendsSaleRights=62
    BondsCouponRunPayment=63
    BondsCouponRunIncome=65
    BondsCoupon=66
    CreditCardRefund=67
    DerivativesAdjustment=68
    DerivativesGuarantee=70
    DerivativesCommission=72
    RolloverPaid=75
    RolloverReceived=76

## Sets if a Historical Chart must adjust splits or dividends with splits or do nothing
class eHistoricalChartAdjusts:
    ## Without splits nor dividens
    NoAdjusts=0
    ## WithSplits
    Splits=1
    ##With splits and dividends
    SplitsAndDividends=2#Dividends with splits.        


class eLeverageType:
    Variable=-1
    NotLeveraged=1
    X2=2
    X3=3
    X4=4
    X5=5
    X10=10
    X20=20
    X25=25
    X50=50
    X100=100
    X200=200
    X500=500
    X1000=1000

class eMoneyCurrency:
    Product=1
    Account=2
    User=3

## Type definition to refer to long /short invesment type positions
class eInvestmentTypePosition:
    Long=1
    Short=2
            
    ## Return True if it's short. Due to postgres database has this definition
    @classmethod
    def to_boolean(self, einvestmenttypeposition):
        if einvestmenttypeposition==1:
            return False
        return True

    ## Returns Short if boolean is true
    @classmethod
    def to_eInvestmentTypePosition(self, boolean):
        if boolean==True:
            return eInvestmentTypePosition.Short
        return eInvestmentTypePosition.Long


RANGE_RECOMENDATION_CHOICES =( 
    (0, _("None")), 
    (1, _("All")), 
    (2, _("SMA 10, 50, 200")), 
    (3, _("SMA 100")), 
    (4, _("Strict SMA 10, 50, 200")), 
    (5, _("Strict SMA 100")), 
    (6, _("Strict SMA 10, 100")), 
)
PCI_CHOICES =( 
    ('c', _("Call")), 
    ('p', _("Put")), 
    ('i', _("Inline")), 
)
CURRENCY_CHOICES =( 
    ('EUR', _("EURO")), 
    ('USD', _("USA Dolar")), 
    ('GBP', _("Inline")), 
)

class Accounts(models.Model):
    name = models.TextField(blank=True, null=True)
    banks = models.ForeignKey('Banks',  models.DO_NOTHING, related_name="accounts", blank=False, null=False)
    active = models.BooleanField(blank=False, null=False)
    number = models.CharField(max_length=24, blank=True, null=True)
    currency = models.TextField()

    class Meta:
        managed = False
        db_table = 'accounts'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return "{} ({})".format(self.name, self.banks.name)
        
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

## This model is not in Xulpymoney to avoid changing a lot of code
class Stockmarkets(models.Model):
    id = models.IntegerField(primary_key=True)
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
    operationstypes = models.ForeignKey('Operationstypes', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    datetime = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
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
        
    def is_creditcardbilling(self):
        if self.concepts.id==eConcept.CreditCardBilling:
            return True
        return False
    def is_transfer(self):
        if Comment().getCode(self.comment) in (eComment.AccountTransferOrigin, eComment.AccountTransferDestiny, eComment.AccountTransferOriginCommission):
            return True
        return False
        
    def is_investmentoperation(self):
        if Comment().getCode(self.comment) in (eComment.InvestmentOperation, ):
            return True
        return False

class Annualtargets(models.Model):
    year = models.IntegerField(primary_key=True)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'annualtargets'



class Banks(models.Model):
    name = models.TextField()
    active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'banks'      

    def __str__(self):
        return self.name

    def balance_accounts(self):
        if hasattr(self, "_balance_accounts") is False:
            qs=Accounts.objects.all().filter(banks_id=self.id, active=True)
            self._balance_accounts=accounts_balance_user_currency(qs,  timezone.now())
        return self._balance_accounts

    def balance_investments(self, request):
        from moneymoney.investmentsoperations import InvestmentsOperationsTotalsManager_from_investment_queryset
        if hasattr(self, "_balance_investments") is False:
            iotm=InvestmentsOperationsTotalsManager_from_investment_queryset(self.investments(active=True), timezone.now(), request)
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
        managed = False
        db_table = 'concepts'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return "{} - {}".format(_(self.name), _(self.operationstypes.name))
        
    @staticmethod
    def dictionary():
        d={}
        for o in Concepts.objects.all():
            d[o.id]=o.fullName()
        return d
        
    def queryset_order_by_fullname():
        ids=[]
        for concept in sorted(Concepts.objects.select_related("operationstypes").all(), key=lambda o: o.fullName()):
            ids.append(concept.id)
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
        queryset = Concepts.objects.select_related("operationstypes").filter(pk__in=ids).order_by(preserved)
        return queryset
        
    ## Esta función fue optimizada de 23 queries y 8.43 ms a 7 queries en 4.79ms
    def queryset_for_dividends_order_by_fullname():
        ids=[]
        for concept in sorted(Concepts.objects.select_related('operationstypes').filter(pk__in=(
        eConcept.Dividends, eConcept.AssistancePremium,  eConcept.DividendsSaleRights, eConcept.RolloverPaid, eConcept.RolloverReceived, eConcept.BondsCouponRunPayment, eConcept.BondsCouponRunIncome, eConcept.BondsCoupon)), key=lambda o: o.fullName()):
            ids.append(concept.id)
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
        queryset = Concepts.objects.select_related('operationstypes').filter(pk__in=ids).order_by(preserved)
        return queryset    

    def queryset_for_accountsoperations_order_by_fullname():
        ids=[]
        for concept in sorted(Concepts.objects.select_related('operationstypes').filter(operationstypes_id__in=(
            eOperationType.Income,  
            eOperationType.Expense,  
            eOperationType.DerivativeManagement
        )), key=lambda o: o.fullName()):
            ids.append(concept.id)
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
        queryset = Concepts.objects.select_related('operationstypes').filter(pk__in=ids).order_by(preserved)
        return queryset


class Creditcards(models.Model):
    name = models.TextField()
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    deferred = models.BooleanField()
    maximumbalance = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    active = models.BooleanField()
    number = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
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
    operationstypes = models.ForeignKey('Operationstypes', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    creditcards = models.ForeignKey(Creditcards, models.DO_NOTHING)
    paid = models.BooleanField()
    paid_datetime = models.DateTimeField(blank=True, null=True)
    accountsoperations= models.ForeignKey('Operationstypes', models.DO_NOTHING, null=True,  related_name="paid_accountsoperations")
    datetime = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
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
        managed = False
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
        dividends=cursor_one_field("""
    select 
        sum(net) 
    from 
        dividends 
    where 
        datetime>=%s and
        datetime<=%s  and
        investments_id in %s
    """, (from_dt, to_dt, tuple(ids) ))
        if dividends is None:
            dividends=0
        return dividends
        

    ## TODO This method should take care of diffrent currencies in accounts. Dividens are in account currency
    @staticmethod
    def net_gains_baduser_between_datetimes(from_dt,  to_dt):
        dividends=cursor_one_field("""
    select 
        sum(net) 
    from 
        dividends 
    where 
        datetime>=%s and
        datetime<=%s  
    """, (from_dt, to_dt ))
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
            c.operationstypes=self.concepts.operationstypes
            c.amount=self.net
            #c.comment="Transaction not finished"
            c.comment=Comment().encode(eComment.Dividend, self)
            c.accounts=self.investments.accounts
            c.save()
            self.accountsoperations=c
        else:#update
            self.accountsoperations.datetime=self.datetime
            self.accountsoperations.concepts=self.concepts
            self.accountsoperations.operationstypes=self.concepts.operationstypes
            self.accountsoperations.amount=self.net
            self.accountsoperations.comment=Comment().encode(eComment.Dividend, self)
            self.accountsoperations.accounts=self.investments.accounts
            self.accountsoperations.save()
        self.save()

class Dps(models.Model):
    date = models.DateField(blank=True, null=True)
    gross = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    products = models.ForeignKey('Products', models.DO_NOTHING, blank=True, null=True)
    paydate = models.DateField()

    class Meta:
        managed = False
        db_table = 'dps'

## django no funciona con 2 primary keys, así que hago los inserts manuales
class EstimationsDps(models.Model):
    year = models.IntegerField(primary_key=True)
    estimation = models.DecimalField(max_digits=18, decimal_places=6)
    date_estimation = models.DateField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    manual = models.BooleanField(blank=True, null=True)
    products= models.ForeignKey('Products', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'estimations_dps'
        unique_together = (('year', 'products'),)


class EstimationsEps(models.Model):
    year = models.IntegerField(primary_key=True)
    estimation = models.DecimalField(max_digits=18, decimal_places=6)
    date_estimation = models.DateField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    manual = models.BooleanField(blank=True, null=True)
    products= models.ForeignKey('Products', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'estimations_eps'
        unique_together = (('year', 'products'),)


class Globals(models.Model):
    global_field = models.TextField(db_column='global', primary_key=True)  # Field renamed because it was a Python reserved word.
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'globals'


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
        managed = False
        db_table = 'investments'
        ordering = ['name']
        

    def __str__(self):
        return self.fullName()

    def fullName(self):
        return "{} ({})".format(self.name, self.accounts.name)
            
    ## Used to display bank order execution alert using form cleaned_data
    @staticmethod
    def bank_alert(cleaned_data):
        return _(f"""<p>Investment was updated sucessfully.</p>
        <p>Don't forget to set this information to your bank if neccessary:</p>
        <ul>
            <li>Selling price: {Currency(cleaned_data['selling_price'], cleaned_data["products"].currency)}</li>
            <li>Expiration selling order: {cleaned_data['selling_expiration']}</li>
        </ul>
        """)
        
    def operations(self, request, local_currency):
        if hasattr(self, "_operations") is False:
            from moneymoney.investmentsoperations import InvestmentsOperations_from_investment
            self._operations=InvestmentsOperations_from_investment(request, self, timezone.now(), local_currency)
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
        managed = False
        db_table = 'investmentsoperations'
        
    def __str__(self):
        return "InvestmentOperation"


    def delete(self):
        execute("delete from investmentsaccountsoperations where investmentsoperations_id=%s",(self.id, )) 
        models.Model.delete(self)
        


    ## Esta función actualiza la tabla investmentsaccountsoperations que es una tabla donde 
    ## se almacenan las accountsoperations automaticas por las operaciones con investments. Es una tabla 
    ## que se puede actualizar en cualquier momento con esta función
    @transaction.atomic
    def update_associated_account_operation(self,  request):
        #/Borra de la tabla investmentsaccountsoperations los de la operinversión pasada como parámetro
        execute("delete from investmentsaccountsoperations where investmentsoperations_id=%s",(self.id, )) 

        investment_operations=InvestmentsOperations_from_investment(request, self.investments, timezone.now(), request.local_currency)
        io=investment_operations.o_find_by_id(self.id)
        
        if self.investments.daily_adjustment is True: #Because it uses adjustment information
            return
        
        comment=Comment().encode(eComment.InvestmentOperation, self)
        if self.operationstypes.id==4:#Compra Acciones
            c=Investmentsaccountsoperations()
            c.datetime=self.datetime
            c.concepts=Concepts.objects.get(pk=29)
            c.operationstypes=c.concepts.operationstypes
            c.amount=-io['net_account']
            c.comment=comment
            c.accounts=self.investments.accounts
            c.investments=self.investments
            c.investmentsoperations=self
            c.save()
        elif self.operationstypes.id==5:#// Venta Acciones
            c=Investmentsaccountsoperations()
            c.datetime=self.datetime
            c.concepts=Concepts.objects.get(pk=35)
            c.operationstypes=c.concepts.operationstypes
            c.amount=io['net_account']
            c.comment=comment
            c.accounts=self.investments.accounts
            c.investments=self.investments
            c.investmentsoperations=self
            c.save()
        elif self.operationstypes.id==6:#Added
            if(self.commission!=0):
                c=Investmentsaccountsoperations()
                c.datetime=self.datetime
                c.concepts=Concepts.objects.get(pk=38)
                c.operationstypes=c.concepts.operationstypes
                c.amount=-io['taxes_account']-io['commission_account']
                c.comment=comment
                c.accounts=self.investments.accounts
                c.investments=self.investments
                c.investmentsoperations=self
                c.save()




class Investmentsaccountsoperations(models.Model):
    concepts = models.ForeignKey('Concepts', models.DO_NOTHING)
    operationstypes =models.ForeignKey('Operationstypes', models.DO_NOTHING, blank=False, null=False)
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    accounts = models.ForeignKey(Accounts, models.DO_NOTHING)
    datetime = models.DateTimeField(blank=True, null=True)
    investmentsoperations = models.ForeignKey(Investmentsoperations, models.DO_NOTHING)
    investments = models.ForeignKey(Investments, models.DO_NOTHING, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'investmentsaccountsoperations'


    
class Leverages(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField()
    multiplier = models.DecimalField(max_digits=100, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'leverages'

    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

class Operationstypes(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'operationstypes'
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)
        
    @staticmethod
    def dictionary():
        d={}
        for ot in Operationstypes.objects.all():
            d[ot.id]=ot.fullName()
        return d

class Opportunities(models.Model):
    date = models.DateField()
    removed = models.DateField(blank=True, null=True)
    executed = models.DateField(blank=True, null=True)
    entry = models.DecimalField(max_digits=100, decimal_places=2)
    products = models.ForeignKey('Products', models.DO_NOTHING)
    target = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    stoploss = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    short = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'opportunities'


class Orders(models.Model):
    date = models.DateField()
    expiration = models.DateField()
    shares = models.DecimalField(max_digits=100, decimal_places=6, blank=True, null=True)
    price = models.DecimalField(max_digits=100, decimal_places=2, blank=True, null=True)
    investments = models.ForeignKey(Investments, models.DO_NOTHING)
    executed = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'orders'
        
    def currency_amount(self):
        return Currency(self.price*self.shares*self.investments.products.real_leveraged_multiplier(), self.investments.products.currency)
        
    def needs_stop_loss_warning(self):
        if self.shares>0 and self.price>self.investments.products.basic_results()["last"]:
            return True
        elif  self.shares<0 and self.price<self.investments.products.basic_results()["last"]:
            return True
        return False

    ## Used to display bank order execution alert using form cleaned_data
    @staticmethod
    def bank_alert(cleaned_data, warning=False):
        if warning==True:
            stw='<p><span class="red">' + _("Remember that is a stop loss order")+'</span></p>'
        else:
            stw=""
        
        return _(f"""<p>Order was created sucessfully.</p>
        <p>Don't forget to set this order in your bank:</p>
        {stw}
        <ul>
            <li>Expiration: {cleaned_data['expiration']}</li>
            <li>Investment: {cleaned_data['investments'].fullName()}</li>
            <li>Shares: {cleaned_data['shares']} </li>
            <li>Price: {Currency(cleaned_data['price'], cleaned_data['investments'].products.currency)} </li>
        </ul>
        """)

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
    tickers = models.TextField(blank=True, null=True)  # This field type is a guess.
    high_low = models.BooleanField(blank=True, null=True)
    decimals = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'
        ordering = ['name']
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return "{} ({})".format(self.name, self.id)
        
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
        return Products.objects.filter(id__in=RawSQL('select products.id from products, investments where products.id=investments.products_id and investments.active is true', ()))


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
        

class Productstypes(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'productstypes'
        
    def __str__(self):
        return self.fullName()
        
    def fullName(self):
        return _(self.name)

class Quotes(models.Model):
    id = models.AutoField(primary_key=True)
    datetime = models.DateTimeField(blank=True, null=True)
    quote = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    products = models.ForeignKey(Products, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'quotes'
        
    def __str__(self):
        return f"Quote ({self.id}) of '{self.products.name}' at {self.datetime} is {self.quote}"
        
    def save(self):
        quotes=Quotes.objects.all().filter(datetime=self.datetime, products=self.products)
        if quotes.count()>0:
            for quote in quotes:
                quote.quote=self.quote
                models.Model.save(quote)
                return (f"Updating {quote}")
        else:
            models.Model.save(self)
            return (f"Inserting {self}")


class Simulations(models.Model):
    database = models.TextField(blank=True, null=True)
    starting = models.DateTimeField(blank=True, null=True)
    ending = models.DateTimeField(blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)
    creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'simulations'


class Splits(models.Model):
    datetime = models.DateTimeField()
    products = models.ForeignKey(Products, models.DO_NOTHING)
    before = models.IntegerField()
    after = models.IntegerField()
    comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'splits'


class StrategiesTypes(models.IntegerChoices):
    Generic = 0, _('Genéric') #additional { }
    PairsInSameAccount = 1, _('Pairs in same account') #additional {"worse":_, "better":_ "account" }
    Ranges = 2,  _('Product ranges')

class Strategies(models.Model):
    name = models.TextField()
    investments = models.TextField(blank=True, null=True)
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
        managed = False
        db_table = 'strategies'
        ordering = ['name']

    ## Generates the url of details. I got errors in template reversing
    def url_details(self):
        if self.type==StrategiesTypes.PairsInSameAccount:
            if self.additional1 is not None and self.additional2 is not None or self.additional3 is not None:
                return reverse_lazy('investment_pairs',args=(self.additional1, self.additional2, self.additional3))
            else:
                return ""
            
            #additional1=products_id, additional2=percentage_between_ranges*1000, additional3=percentage_gains*1000, additional4=amount,additional5=recomendationmethod,additional6=onlyfirst,additional7=accounts_id}
        elif self.type==StrategiesTypes.Ranges:
            return reverse_lazy('product_ranges')+f"?product={self.additional1}&percentagebetween={self.additional2}&percentagegains={self.additional3}&amount={self.additional4}&method={self.additional5}&onlyfirst={self.additional6}&account={self.additional7}"
        
    ## Replaces None for dt_to and sets a very big datetine
    def dt_to_for_comparations(self):
        if self.dt_to is None:
            return timezone.now()
        return self.dt_to

def percentage_to_selling_point(shares, selling_price, last_quote):       
    """Función que calcula el tpc selling_price partiendo de las el last y el valor_venta
    Necesita haber cargado mq getbasic y operinversionesactual"""
    if selling_price==0 or selling_price==None:
        return Percentage()
    if shares>0:
        return Percentage(selling_price-last_quote, last_quote)
    else:#Long short products
        return Percentage(-(selling_price-last_quote), last_quote)

def currencies_in_accounts():
    return cursor_one_column("select distinct(currency) from accounts")
    
## @return accounts, investments, totals, invested
def total_balance(dt, local_currency):
    return cursor_one_row("select * from total_balance(%s,%s)", (dt, local_currency, ))

def money_convert(dt, amount, from_,  to_):   
    if from_==to_:
        return amount
    return cursor_one_field("select * from money_convert(%s, %s, %s, %s)", (dt, amount, from_,  to_))

## This method should take care of diffrent currencies
def balance_user_by_operationstypes(year,  month,  operationstypes_id, local_currency, local_zone):
    r=0
    for currency in currencies_in_accounts():
        for row in cursor_rows("""
            select sum(amount) as amount 
            from 
                accountsoperations,
                accounts
            where 
                operationstypes_id=%s and 
                date_part('year',datetime)=%s and
                date_part('month',datetime)=%s and
                accounts.currency=%s and
                accounts.id=accountsoperations.accounts_id   
        union all 
            select sum(amount) as amount 
            from 
                creditcardsoperations ,
                creditcards,
                accounts
            where 
                operationstypes_id=%s and 
                date_part('year',datetime)=%s and
                date_part('month',datetime)=%s and
                accounts.currency=%s and
                accounts.id=creditcards.accounts_id and
                creditcards.id=creditcardsoperations.creditcards_id""", (operationstypes_id, year, month,  currency, operationstypes_id, year, month,  currency)):

            if row['amount'] is not None:
                if local_currency==currency:
                    r=r+row['amount']
                else:
                    r=r+money_convert(dtaware_month_end(year, month, local_zone), row['amount'], currency, local_currency)
    return r

def accounts_balance_user_currency(qs, dt):
    if len (qs)==0:
        return 0
    return cursor_one_field("select sum((account_balance(accounts.id,%s,'EUR')).balance_user_currency) from  accounts where id in %s", (dt, qs_list_of_ids(qs)))



def qs_list_of_ids(qs):
    r=[]
    for o in qs:
        r.append(o.id)
    return tuple(r)

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
                aoo=Accountsoperations.objects.get(pk=args[0])
                aod=Accountsoperations.objects.get(pk=args[1])
                return _("Comission transfering {} from {} to {}").format(Currency(aoo.amount, aoo.accounts.currency), aoo.accounts.name, aod.accounts.name)

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
                print(operaccount)
                return {"creditcard":creditcard, "operaccount":operaccount}

            elif code==eComment.CreditCardRefund:#Devolución de tarjeta
                if not self.validateLength(1, code, args): return string
                cco=Creditcardsoperations.objects.get(pk=args[0])
                money=Currency(cco.amount, cco.creditcards.accounts.currency)
                return _("Refund of {} payment of which had an amount of {}").format(dtaware2string(cco.datetime), money)

#def queryset_investments_load_basic_results(qs_investments):
#    products_ids=tuple(qs_investments.values_list('products__id',flat=True))
#    basic_results=cursor_rows_as_dict("id", "select t.* from products, last_penultimate_lastyear(products.id, now()) as t where products.id in %s",  products_ids)
#    print(basic_results)
#    for investment in qs_investments:
#        investment.products._basic_results=basic_results[investment.products.id]
