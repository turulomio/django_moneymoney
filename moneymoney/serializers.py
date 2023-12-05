from datetime import date
from django.db import transaction
from moneymoney import models
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from request_casting.request_casting import id_from_url


class SuccessSerializer(serializers.Serializer):
    success=serializers.BooleanField()
    detail = serializers.CharField()


class BanksSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Banks
        fields = ('url', 'name', 'active', 'id', 'localname')

    def get_localname(self, obj):
        return  _(obj.name)

class AccountsSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    fullname = serializers.SerializerMethodField()
    class Meta:
        model = models.Accounts
        fields = ('url', 'id','name', 'active', 'number','currency','banks', 'localname', 'fullname', 'decimals')

    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)
        
        
    @extend_schema_field(OpenApiTypes.STR)
    def get_fullname(self, obj):
        return  obj.fullName()
        
        
class DividendsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    class Meta:
        model = models.Dividends
        fields = ('url', 'id', 'investments', 'gross','taxes','net', 'dps', 'datetime', 'accountsoperations', 'commission', 'concepts', 'currency_conversion',  'currency')

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return  _(obj.investments.accounts.currency)

class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    fullname = serializers.SerializerMethodField()
    class Meta:
        model = models.Investments
        fields = ('url', 'id','name', 'active','accounts', 'selling_price', 'products',  'selling_expiration', 'daily_adjustment', 'balance_percentage', 'fullname', 'decimals')

    @extend_schema_field(OpenApiTypes.STR)
    def get_fullname(self, obj):
        return obj.fullName()

class InvestmentsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    class Meta:
        model = models.Investmentsoperations
        fields = ('url', 'id','operationstypes', 'investments','shares', 'taxes', 'commission',  'price', 'datetime', 'comment', 'currency_conversion', 'currency')

    @transaction.atomic
    def create(self, validated_data):
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        created.save()
        created.investments.set_attributes_after_investmentsoperations_crud()
        created.update_associated_account_operation(self.context.get("request"))
        return created
    
    @transaction.atomic
    def update(self, instance, validated_data):
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        updated.save()
        updated.investments.set_attributes_after_investmentsoperations_crud()
        updated.update_associated_account_operation(self.context.get("request"))
        return updated
        

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return  _(obj.investments.products.currency)

class ConceptsSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Concepts
        fields = ('url', 'id', 'name',  'operationstypes', 'editable', 'localname')
    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)

class CreditcardsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Creditcards
        fields = ('url', 'id', 'name',  'number', 'accounts', 'maximumbalance', 'deferred', 'active')
        
class CreditcardsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Creditcardsoperations
        fields = ('url', 'id', 'datetime', 'concepts', 'amount','comment','creditcards', 'paid','paid_datetime', 'currency')
    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return  obj.creditcards.accounts.currency
        
        
class DpsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Dps
        fields = ('url', 'id',  'date',  'paydate', 'gross', 'products')
        
class EstimationsDpsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.EstimationsDps
        fields = ('url', 'id','year',  'estimation', 'products', 'date_estimation')
    
    def create(self, validated_data):
        validated_data["date_estimation"]=date.today()
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        return created

class OperationstypesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Operationstypes
        fields = ('url', 'id', 'name', 'localname')

    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)
        
class AccountsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    comment_decoded = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Accountsoperations
        fields = ('id','url', 'datetime', 'concepts', 'amount','comment','accounts',  'currency', 'comment_decoded')
    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return obj.accounts.currency
    @extend_schema_field(OpenApiTypes.STR)
    def get_comment_decoded(self, obj):
        return models.Comment().decode(obj.comment), 
                
class LeveragesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Leverages
        fields = ('url', 'id', 'name', 'multiplier', 'localname')

    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)

class OrdersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Orders
        fields = ('url', 'id', 'date', 'expiration',  'shares', 'price','investments','executed')
        
class ProductsSerializer(serializers.HyperlinkedModelSerializer):
    real_leveraged_multiplier = serializers.SerializerMethodField()
    flag=serializers.SerializerMethodField()
    fullname=serializers.SerializerMethodField()
    uses=serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Products
        fields = ('url', 'id', 'name',  'isin', 'currency','productstypes','agrupations', 'web', 'address', 'phone', 'mail', 'percentage', 'pci', 'leverages', 'stockmarkets', 'comment',  'obsolete', 'ticker_yahoo', 'ticker_morningstar','ticker_google','ticker_quefondos','ticker_investingcom', 'decimals', 'real_leveraged_multiplier', 'fullname', 'uses', 'flag')
    
    def create(self, validated_data):
        request=self.context.get("request")
        if request.data["system"] is True :
            validated_data["id"]=models.Products.next_system_products_id()
        else:
            last=models.Products.objects.latest('id')
            if last.id<10000000:#First personal data
                validated_data["id"]=10000001
            else:
                validated_data["id"]=last.id +1
            
        ## AQUI SE DEBERÏA HACER ALGUN TIPO DE BLOQUEO DE TABLA SI FUERA UNA BASE DE DATOS MULTIUSUARIO
        ## PARA RESERVAR ESTE ID MANUAL
        
        if  not request.user.groups.filter(name="CatalogManager").exists():
           if  request.data["system"] is True:
                raise ValidationError(_("You can't edit a system product if you're not a Catalog Manager (only developers)"))
            
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        return created
        
    def update(self, instance, validated_data):
        request=self.context.get("request")       
        if  request.user.groups.filter(name="CatalogManager").exists() is False and id_from_url(request.data["url"])<100000000:
            raise ValidationError(_("You can't edit a system product if you're not a Catalog Manager (only developers)"))
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        return updated
        
    @extend_schema_field(OpenApiTypes.INT)
    def get_real_leveraged_multiplier(self, obj):
        return  obj.real_leveraged_multiplier()

    @extend_schema_field(OpenApiTypes.STR)
    def get_fullname(self, obj):
        return  obj.fullName()

    @extend_schema_field(OpenApiTypes.STR)
    def get_flag(self, obj):
        return  obj.stockmarkets.country

class ProductspairsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Productspairs
        fields = ('url', 'id', 'name', 'a',  'b')

class ProductstypesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Productstypes
        fields = ('url', 'id', 'name', 'localname')

    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)

class QuotesSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.SerializerMethodField()
    decimals = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    class Meta:
        model = models.Quotes
        fields = ('url', 'id', 'datetime', 'quote',  'products', 'name', 'decimals', 'currency')      

    @extend_schema_field(OpenApiTypes.STR)
    def get_name(self, obj):
        return  obj.products.name
    @extend_schema_field(OpenApiTypes.INT)
    def get_decimals(self, obj):
        return  obj.products.decimals
    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return  obj.products.currency
    
class StockmarketsSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.Stockmarkets
        fields = ('url', 'id', 'name', 'country', 'starts', 'closes', 'starts_futures',  'closes_futures', 'zone', 'localname')

    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)

class StrategiesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Strategies
        fields = ('url', 'id', 'name',  'investments', 'dt_from','dt_to','type','comment','additional1','additional2','additional3','additional4','additional5','additional6','additional7','additional8','additional9','additional10')


class FastOperationsCoverageSerializer(serializers.HyperlinkedModelSerializer):
    
    currency= serializers.SerializerMethodField()
    class Meta:
        model = models.FastOperationsCoverage
        fields = ('url', 'id', 'datetime', 'investments', 'amount','comment', 'currency')

    def get_currency(self, o):
        return o.investments.products.currency
