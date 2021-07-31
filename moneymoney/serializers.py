from  moneymoney.models import (
    Accounts, 
    Accountsoperations, 
    Banks, 
    Concepts, 
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
class OperationstypesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Operationstypes
        fields = ('url', 'id', 'name')
        
class AccountsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Accountsoperations
        fields = ('url', 'datetime', 'concepts',  'operationstypes', 'amount','comment','accounts')
