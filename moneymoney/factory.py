from factory import Faker, SubFactory, lazy_attribute
from factory.django import DjangoModelFactory
from moneymoney import models
#https://faker.readthedocs.io/en/master/providers/faker.providers.currency.html

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
        
        

class LeveragesFactory(DjangoModelFactory):
    class Meta:
        model= models.Leverages
        
    multiplier = Faker("random_int")
    
    @lazy_attribute
    def name(self):
        return f'Leverage x{self.multiplier}'


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

class ProductsFactory(DjangoModelFactory):
    class Meta:
        model= models.Products
        
    name = Faker("bothify", text="Product ??????")
    isin=""
    currency=""
    productstypes=SubFactory(ProductstypesFactory)
    agrupations=None
    web=None
    address=None
    phone=None
    mail=None
    percentage=100
    pci="c"
    leverages=SubFactory(LeveragesFactory)
    stockmarkets = SubFactory(StockmarketsFactory)
    comment = None
    obsolete = Faker("boolean")
    ticker_google = None
    ticker_yahoo = None
    ticker_morningstar = None
    ticker_quefondos = None
    ticker_investingcom = None
    decimals =2

class InvestmentsFactory(DjangoModelFactory):
    class Meta:
        model= models.Investments
        
    name = Faker("bothify", text="Investment ??????")
    active = Faker("boolean")
    accounts = SubFactory(AccountsFactory)
    selling_price = None
    products = SubFactory(ProductsFactory)
    selling_expiration = None
    daily_adjustment = False
    balance_percentage= 100
        
class OperationstypesFactory(DjangoModelFactory):
    class Meta:
        model= models.Operationstypes
        
    name = Faker("bothify", text="Operation type ??????")

class ConceptsFactory(DjangoModelFactory):
    class Meta:
        model= models.Concepts
        
    operationstypes=SubFactory(OperationstypesFactory)
    name = Faker("bothify", text="Concept ??????")
    editable = Faker("boolean")



class LeveragesFactory(DjangoModelFactory):
    class Meta:
        model= models.Leverages
        
    multiplier = Faker("random_int")
    
    @lazy_attribute
    def name(self):
        return f'Leverage x{self.multiplier}'
