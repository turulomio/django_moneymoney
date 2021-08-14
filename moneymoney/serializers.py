from  moneymoney.models import (
    Accounts, 
    Accountsoperations, 
    Banks, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Investments, 
    Operationstypes, 
    Strategies, 
)
from rest_framework import serializers

class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'id')

class AccountsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Accounts
        fields = ('url', 'name', 'active', 'number','currency','banks')

class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts')
        
class ConceptsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Concepts
        fields = ('url', 'id', 'name',  'operationstypes', 'editable')

class CreditcardsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Creditcards
        fields = ('url', 'id', 'name',  'number', 'accounts', 'maximumbalance', 'deferred', 'active')
        
class CreditcardsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Creditcardsoperations
        fields = ('url', 'datetime', 'concepts',  'operationstypes', 'amount','comment','creditcards', 'paid','paid_datetime')

class OperationstypesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Operationstypes
        fields = ('url', 'id', 'name')
        
class AccountsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Accountsoperations
        fields = ('url', 'datetime', 'concepts',  'operationstypes', 'amount','comment','accounts')

class StrategiesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Strategies
        fields = ('url', 'id', 'name',  'investments', 'dt_from','dt_to','type','comment','additional1','additional2','additional3','additional4','additional5','additional6','additional7','additional8','additional9','additional10')
