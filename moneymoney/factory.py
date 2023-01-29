from factory import Faker, SubFactory, lazy_attribute, Iterator
from factory.django import DjangoModelFactory
from moneymoney import models
from django.utils import timezone
# https://faker.readthedocs.io/en/master/providers/faker.providers.currency.html

class LeveragesFactory(DjangoModelFactory):
    class Meta:
        model= models.Leverages
        
    multiplier = Faker("random_int")
    
    @lazy_attribute
    def name(self):
        return f'Leverage x{self.multiplier}'
        
class BanksFactory(DjangoModelFactory):
    class Meta:
        model= models.Banks
        
    name = Faker("company")
    active = Faker("boolean")
        
class AccountsFactory(DjangoModelFactory):
    class Meta:
        model= models.Accounts
        
    active = Faker("boolean")
    banks=SubFactory(BanksFactory)
    number=Faker("random_number", digits=20,  fix_len=True)
    currency=Faker("currency_code")
    decimals=Faker("random_int", min=0, max=6)
    
    
    @lazy_attribute
    def name(self):
        return f"{self.banks.name} Account"

class ProductstypesFactory(DjangoModelFactory):
    class Meta:
        model= models.Productstypes
        
    name = Faker("bothify", text="Product type ??????")

class StockmarketsFactory(DjangoModelFactory):
    class Meta:
        model= models.Stockmarkets
        
    name = Faker("bothify", text="Stockmarket ??????")
    country="es"
    starts="09:00:00"
    closes="20:00:00"
    starts_futures="09:00:00"
    closes_futures="20:00:00"
    zone="Europe/Madrid"


class ProfileFactory(DjangoModelFactory):
    class Meta:
        model= models.Profile

class ProductsFactory(DjangoModelFactory):
    class Meta:
        model= models.Products
        
    name = Faker("bothify", text="Product ??????")
    isin=""
    currency=Faker("currency_code")
    productstypes=SubFactory(ProductstypesFactory)
    agrupations=""
    web=Faker("uri")
    address=Faker("address")
    phone=Faker("phone_number")
    mail=Faker("ascii_email")
    percentage=100
    pci="c"
    leverages=SubFactory(LeveragesFactory)
    stockmarkets = SubFactory(StockmarketsFactory)
    comment = Faker("sentence")
    obsolete = Faker("boolean")
    ticker_google = ""
    ticker_yahoo = ""
    ticker_morningstar = ""
    ticker_quefondos = ""
    ticker_investingcom = ""
    decimals =2
    

class QuotesFactory(DjangoModelFactory):
    class Meta:
        model= models.Quotes
    datetime = Faker("date_time", tzinfo=timezone.get_current_timezone())
    quote = Faker("random_number")
    products = SubFactory(ProductsFactory)

class InvestmentsFactory(DjangoModelFactory):
    class Meta:
        model= models.Investments
        
    name = Faker("bothify", text="Investment ??????")
    active = Faker("boolean")
    accounts = SubFactory(AccountsFactory)
    selling_price = Faker("random_int")
    products = Iterator(models.Products.objects.all())
    selling_expiration = Faker("date")
    daily_adjustment = False
    balance_percentage= 100
        

class OperationstypesFactory(DjangoModelFactory):
    class Meta:
        model= models.Operationstypes
        
    name = Faker("bothify", text="Operation type ??????")

class InvestmentsoperationsFactory(DjangoModelFactory):
    class Meta:
        model= models.Investmentsoperations
        
    operationstypes = SubFactory(OperationstypesFactory)
    investments = SubFactory(InvestmentsFactory)
    shares=Faker("random_int")
    price=Faker("random_number")
    taxes=Faker("random_number")
    commission=Faker("random_number")
    datetime=timezone.now()
    comment=Faker("sentence")
    show_in_ranges=Faker("boolean")
    currency_conversion=1
    

class ConceptsFactory(DjangoModelFactory):
    class Meta:
        model= models.Concepts
        
    operationstypes=SubFactory(OperationstypesFactory)
    name = Faker("bothify", text="Concept ??????")
    editable = Faker("boolean")


class EstimationsDpsFactory(DjangoModelFactory):
    class Meta:
        model= models.EstimationsDps
    
    year=Faker("year")
    estimation=Faker("random_number")
    products = Iterator(models.Products.objects.all())
    date_estimation=Faker("date")
        
        
class AccountsoperationsionsFactory(DjangoModelFactory):
    class Meta:
        model= models.Accountsoperations
    concepts = SubFactory(ConceptsFactory)
    amount=Faker("random_number")
    comment=Faker("sentence")
    accounts=SubFactory(AccountsFactory)
    datetime=timezone.now()


class CreditcardsFactory(DjangoModelFactory):
    class Meta:
        model= models.Creditcards
    name = Faker("bothify", text="Credit Card ??????")
    accounts=SubFactory(AccountsFactory)
    deferred= Faker("boolean")
    maximumbalance=Faker("random_number")
    active = Faker("boolean")
    number=Faker("random_number", digits=16,  fix_len=True)
    
    
    
    

class CreditcardsoperationsFactory(DjangoModelFactory):
    class Meta:
        model= models.Creditcardsoperations
    datetime=timezone.now()
    concepts = SubFactory(ConceptsFactory)
    amount = Faker("random_number")
    comment= Faker("sentence")
    creditcards= SubFactory(CreditcardsFactory)
    paid=False
    paid_datetime=None
    accountsoperations=None
    
    
    

class DividendsFactory(DjangoModelFactory):
    class Meta:
        model= models.Dividends
    investments = SubFactory(InvestmentsFactory)
    gross = Faker("random_number")
    taxes = Faker("random_number")
    net = Faker("random_number")
    dps = Faker("random_number")
    datetime = timezone.now()
    accountsoperations = None
    commission = Faker("random_number")
    concepts = SubFactory(ConceptsFactory)
    currency_conversion = 1

class DpsFactory(DjangoModelFactory):
    class Meta:
        model= models.Dps
    
    date = Faker("date")
    gross = Faker("random_number")
    products = Iterator(models.Products.objects.all())
    paydate = Faker("date")
    
    
class OrdersFactory(DjangoModelFactory):
    class Meta:
        model= models.Orders
    
    date = Faker("date")
    expiration = Faker("date")
    shares= Faker("random_number")
    price = Faker("random_number")
    investments = SubFactory(InvestmentsFactory)
    executed = None
    
    
    
    
class ProductspairsFactory(DjangoModelFactory):
    class Meta:
        model= models.Productspairs
    name = Faker("bothify", text="Product Pair ??????")
    a = Iterator(models.Products.objects.all())
    b = Iterator(models.Products.objects.all())
    
