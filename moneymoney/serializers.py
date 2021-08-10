from  moneymoney.models import (
    Accounts, 
    Accountsoperations, 
    Banks, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Investments, 
    Operationstypes, 
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
