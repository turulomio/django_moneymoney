from  moneymoney.models import (
    Accounts, 
    Accountsoperations, 
    Banks, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Dividends, 
    Investments, 
    Investmentsoperations, 
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
        fields = ('url', 'id','name', 'active', 'number','currency','banks')
        
class DividendsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Dividends
        fields = ('url', 'id', 'investments', 'gross','taxes','net', 'dps', 'datetime', 'accountsoperations', 'commission', 'concepts', 'currency_conversion')

    
    def create(self, validated_data):
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        created.update_associated_account_operation()
        return created
    
    def update(self, instance, validated_data):
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        updated.update_associated_account_operation()
        return updated
        
class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    fullname = serializers.SerializerMethodField()
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts', 'selling_price', 'products',  'selling_expiration', 'daily_adjustment', 'balance_percentage', 'fullname')

    def get_fullname(self, obj):
        return obj.fullName()

class InvestmentsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Investmentsoperations
        fields = ('url', 'id','operationstypes', 'investments','shares', 'taxes', 'commission',  'price', 'datetime', 'comment', 'show_in_ranges', 'currency_conversion')

    
    def create(self, validated_data):
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        created.update_associated_account_operation(self.context.get("request"))
        return created
    
    def update(self, instance, validated_data):
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        updated.update_associated_account_operation(self.context.get("request"))
        return updated
        




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
