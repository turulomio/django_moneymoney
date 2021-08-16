from  moneymoney.models import (
    Accounts, 
    Accountsoperations, 
    Banks, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Investments, 
    Leverages, 
    Orders, 
    Operationstypes, 
    Products, 
    Productstypes, 
    Stockmarkets, 
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
        fields = ('url', 'id','name', 'active','accounts', 'selling_price', 'products',  'selling_expiration', 'daily_adjustment', 'balance_percentage')

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
                
class LeveragesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Leverages
        fields = ('url', 'id', 'name', 'multiplier')
class OrdersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Orders
        fields = ('url', 'date', 'expiration',  'shares', 'price','investments','executed')
        
class ProductsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Products
        fields = ('url', 'id', 'name',  'isin', 'currency','productstypes','agrupations', 'web', 'address', 'phone', 'mail', 'percentage', 'pci', 'leverages', 'stockmarkets', 'comment',  'obsolete', 'tickers', 'high_low', 'decimals')
        
class ProductstypesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Productstypes
        fields = ('url', 'id', 'name')        
class StockmarketsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Stockmarkets
        fields = ('url', 'id', 'name')


class StrategiesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Strategies
        fields = ('url', 'id', 'name',  'investments', 'dt_from','dt_to','type','comment','additional1','additional2','additional3','additional4','additional5','additional6','additional7','additional8','additional9','additional10')
