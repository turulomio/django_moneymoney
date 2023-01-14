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
