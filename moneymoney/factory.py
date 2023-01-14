from factory import Faker, SubFactory
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
        
    name = Faker("name")
    active = Faker("boolean")
    banks=SubFactory(BanksFactory)
    number="1223412"
    currency="EUR"
    decimals=2


class LeveragesFactory(DjangoModelFactory):
    class Meta:
        model= models.Leverages
        
    name = Faker("numerify", text='Levrage i%')
    active = Faker("boolean")
