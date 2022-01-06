
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
    Productspairs, 
    Productstypes, 
    Quotes, 
    Stockmarkets, 
    Strategies, 
)
from rest_framework import serializers
from django.utils.translation import gettext as _

class BanksSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'id', 'localname')

    def get_localname(self, obj):
        return  _(obj.name)

class AccountsSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    fullname = serializers.SerializerMethodField()
    class Meta:
        model = Accounts
        fields = ('url', 'id','name', 'active', 'number','currency','banks', 'localname', 'fullname')

    def get_localname(self, obj):
        return  _(obj.name)
        
        
    def get_fullname(self, obj):
        return  obj.fullName()
        
        
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
        created.save()
        created.investments.set_attributes_after_investmentsoperations_crud()
        created.update_associated_account_operation(self.context.get("request"))
        return created
    
    def update(self, instance, validated_data):
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        updated.save()
        updated.investments.set_attributes_after_investmentsoperations_crud()
        updated.update_associated_account_operation(self.context.get("request"))
        return updated

class ConceptsSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = Concepts
        fields = ('url', 'id', 'name',  'operationstypes', 'editable', 'localname')
    def get_localname(self, obj):
        return  _(obj.name)

class CreditcardsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Creditcards
        fields = ('url', 'id', 'name',  'number', 'accounts', 'maximumbalance', 'deferred', 'active')
        
class CreditcardsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    
    class Meta:
        model = Creditcardsoperations
        fields = ('url', 'datetime', 'concepts',  'operationstypes', 'amount','comment','creditcards', 'paid','paid_datetime', 'currency')
    def get_currency(self, obj):
        return  obj.creditcards.accounts.currency
        
        

class OperationstypesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = Operationstypes
        fields = ('url', 'id', 'name', 'localname')

    def get_localname(self, obj):
        return  _(obj.name)
        
class AccountsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    class Meta:
        model = Accountsoperations
        fields = ('url', 'datetime', 'concepts',  'operationstypes', 'amount','comment','accounts',  'currency')
    def get_currency(self, obj):
        return obj.accounts.currency
                
class LeveragesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = Leverages
        fields = ('url', 'id', 'name', 'multiplier', 'localname')

    def get_localname(self, obj):
        return  _(obj.name)

class OrdersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Orders
        fields = ('url', 'date', 'expiration',  'shares', 'price','investments','executed')
        
class ProductsSerializer(serializers.HyperlinkedModelSerializer):
    real_leveraged_multiplier = serializers.SerializerMethodField()
    fullname=serializers.SerializerMethodField()

    class Meta:
        model = Products
        fields = ('url', 'id', 'name',  'isin', 'currency','productstypes','agrupations', 'web', 'address', 'phone', 'mail', 'percentage', 'pci', 'leverages', 'stockmarkets', 'comment',  'obsolete', 'tickers', 'decimals', 'real_leveraged_multiplier', 'fullname')

    def get_real_leveraged_multiplier(self, obj):
        return  obj.real_leveraged_multiplier()

    def get_fullname(self, obj):
        return  obj.fullName()
        
class ProductspairsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Productspairs
        fields = ('url', 'name', 'a',  'b')

class ProductstypesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = Productstypes
        fields = ('url', 'id', 'name', 'localname')

    def get_localname(self, obj):
        return  _(obj.name)

class QuotesSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.SerializerMethodField()
    decimals = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    class Meta:
        model = Quotes
        fields = ('url', 'id', 'datetime', 'quote',  'products', 'name', 'decimals', 'currency')      

    def get_name(self, obj):
        return  obj.products.name
    def get_decimals(self, obj):
        return  obj.products.decimals
    def get_currency(self, obj):
        return  obj.products.currency
    
    def create(self, validated_data):
        quotes=Quotes.objects.all().filter(datetime=validated_data['datetime'], products=validated_data['products'])
        if quotes.count()!=0:
            quotes.delete()
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        return created

class StockmarketsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Stockmarkets
        fields = ('url', 'id', 'name', 'country', 'starts', 'closes', 'starts_futures',  'closes_futures', 'zone')

class StrategiesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Strategies
        fields = ('url', 'id', 'name',  'investments', 'dt_from','dt_to','type','comment','additional1','additional2','additional3','additional4','additional5','additional6','additional7','additional8','additional9','additional10')
