from datetime import date
from django.db import transaction
from moneymoney import models
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer, OpenApiExample
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
        fields = ('url', 'id','operationstypes', 'investments','shares', 'taxes', 'commission',  'price', 'datetime', 'comment', 'currency_conversion', 'currency', 'associated_ao')

    @transaction.atomic
    def create(self, validated_data):
        created=serializers.HyperlinkedModelSerializer.create(self,  validated_data)
        #Checks investment has quotes
        if not models.Quotes.objects.filter(products=created.investments.products).exists():
            raise serializers.ValidationError(_("Investment operation can't be created because its related product hasn't quotes."))

        created.save()
        created.investments.set_attributes_after_investmentsoperations_crud()
        created.update_associated_account_operation(self.context.get("request"))
        return created
    
    @transaction.atomic
    def update(self, instance, validated_data):
        updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
        #Checks investment has quotes
        if not models.Quotes.objects.filter(products=updated.investments.products).exists():
            raise serializers.ValidationError(_("Investment operation can't be updated because its related product hasn't quotes."))

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
        
    def update(self, instance, validated_data):
        # Deferred field can't be updated
        if 'deferred' in validated_data and instance.deferred!=validated_data['deferred']:
            raise ValidationError({'deferred': 'This field cannot be updated'})
        return serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)

class CreditcardsoperationsSerializer(serializers.HyperlinkedModelSerializer):
    currency = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Creditcardsoperations
        fields = ('url', 'id', 'datetime', 'concepts', 'amount','comment','creditcards', 'paid','paid_datetime', 'currency')
        
    def validate(self, data):
        if data["creditcards"].deferred is False:
            raise serializers.ValidationError(_("You can't create a credit card operation with a debit credit card"))
        return serializers.HyperlinkedModelSerializer.validate(self, data)
        
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
    nice_comment = serializers.SerializerMethodField()
    is_editable= serializers.SerializerMethodField()
    associated_io= serializers.SerializerMethodField()
    associated_dividend= serializers.SerializerMethodField()
    
    class Meta:
        model = models.Accountsoperations
        fields = ('id','url', 'datetime', 'concepts', 'amount','comment','accounts',  'currency', 'associated_transfer',  'nice_comment', 'is_editable',  'associated_io', 
        'associated_dividend')

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency(self, obj):
        return obj.accounts.currency

    @extend_schema_field(OpenApiTypes.STR)
    def get_nice_comment(self, obj):
        return  obj.nice_comment()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_editable(self, obj):
        return  obj.is_editable()
        
    @extend_schema_field(OpenApiTypes.URI)
    def get_associated_io(self, obj):
        if hasattr(obj,  "investmentsoperations"):
            request=self.context.get("request")
            return models.Investmentsoperations.hurl(request, obj.investmentsoperations.id)
        return None

    @extend_schema_field(OpenApiTypes.URI)
    def get_associated_dividend(self, obj):
        if hasattr(obj,  "dividends"):
            request=self.context.get("request")
            return models.Dividends.hurl(request, obj.dividends.id)
        return None        

class AccountstransfersSerializer(serializers.HyperlinkedModelSerializer):    
    
    class Meta:
        model = models.Accountstransfers
        fields = ('id','url', 'datetime', 'origin', 'destiny', 'amount','commission','comment','ao_origin',  'ao_destiny', 'ao_commission')
                
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
        fields = ('url', 'id', 'name',  'isin', 'currency','productstypes','agrupations', 'web', 'address', 'phone', 'mail', 'percentage', 'productsstrategies', 'leverages', 'stockmarkets', 'comment',  'obsolete', 'ticker_yahoo', 'ticker_morningstar','ticker_google','ticker_quefondos','ticker_investingcom', 'decimals', 'real_leveraged_multiplier', 'fullname', 'uses', 'flag')
    
    def create(self, validated_data):
        request=self.context.get("request")
        if not "system" in request.data:
            raise ValidationError(_("You must set system parameter to set a system product (True) or a personal product (False)"))
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
        if not "system" in request.data:
            raise ValidationError(_("You must set system parameter to set a system product (True) or a personal product (False)"))
        if request.data["system"] is True:
            if  request.user.groups.filter(name="CatalogManager").exists() is False and id_from_url(request.data["url"])<10000000:
                raise ValidationError(_("You can't edit a system product if you're not a Catalog Manager (only developers)"))
            updated=serializers.HyperlinkedModelSerializer.update(self, instance, validated_data)
            return updated
        else:
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

# Serializer para los campos comunes de la estrategia
class StrategiesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Strategies # Corrected model
        fields = ('url', 'id', 'name', 'dt_from', 'dt_to', 'type', 'comment')
        read_only_fields = ('id', 'url')

# Serializer para EstrategiaMarketing
class StrategiesFastOperationsSerializer(serializers.HyperlinkedModelSerializer):
    """
        Este serializer devuelve:
            - Un objeto strategy
            - "url", "accounts"
    """
    # Anidamos el serializer de Estrategia para manejar los campos comunes
    strategy = StrategiesSerializer()

    class Meta:
        model = models.StrategiesFastOperations
        # Ensure 'url' (if needed, usually for HyperlinkedModelSerializer)
        # 'strategy' for the nested StrategiesSerializer
        # 'accounts' for the ManyToManyField
        fields = ['url', 'strategy', 'accounts']

    def create(self, validated_data):
        # Extraemos los datos de la estrategia base
        strategy_data = validated_data.pop('strategy')
        if strategy_data["type"]!=models.StrategiesTypes.FastOperations:
            raise serializers.ValidationError({"type": "Strategy type is wrong"})
        strategy_instance = models.Strategies.objects.create(**strategy_data)
        sfo_instance = models.StrategiesFastOperations.objects.create(strategy=strategy_instance)
        sfo_instance.accounts.set(validated_data["accounts"])
        return sfo_instance

    def update(self, instance, validated_data):
        # Extraemos los datos de la estrategia base si están presentes
        strategy_data = validated_data.pop('strategy', None)
        # Extraemos los datos de la relación M2M 'accounts'.
        # Use None as default to check if 'accounts' was part of the update payload.
        accounts_data = validated_data.pop('accounts', None)

        if strategy_data:
            if instance.strategy.type!=strategy_data["type"]:
                raise serializers.ValidationError({"type": "You can't change strategy type"})
            # Actualizamos la instancia de Estrategia base usando su serializer
            strategy_serializer = StrategiesSerializer(instance.strategy, data=strategy_data, partial=True, context=self.context)
            strategy_serializer.is_valid(raise_exception=True)
            strategy_serializer.save()

        # Actualizamos los campos directos de StrategiesFastOperations (instance).
        # Since StrategiesFastOperations has no other direct modifiable fields besides the PK (strategy)
        # and M2M (accounts), validated_data should be empty here.
        # If there were other fields, update them manually:
        # for attr, value in validated_data.items():
        #     setattr(instance, attr, value)
        # if validated_data: # Check if there were any fields to update
        #    instance.save(update_fields=validated_data.keys())
        # For this model, super().update() with an empty validated_data is also fine.
        super().update(instance, validated_data) # This is safe if validated_data is empty after pops.

        # Actualizamos la relación M2M 'accounts'
        if accounts_data is not None: # Allows clearing the relation if an empty list is passed for accounts
            instance.accounts.set(accounts_data)

        return instance

# Serializer para EstrategiaMarketing
class StrategiesGenericSerializer(serializers.HyperlinkedModelSerializer):
    # Anidamos el serializer de Estrategia para manejar los campos comunes
    strategy = StrategiesSerializer()

    class Meta:
        model = models.StrategiesGeneric
        # Ensure 'url' (if needed, usually for HyperlinkedModelSerializer)
        # 'strategy' for the nested StrategiesSerializer
        # 'accounts' for the ManyToManyField
        fields = ['url', 'strategy', 'investments']

    def create(self, validated_data):
        # Extraemos los datos de la estrategia base
        strategy_data = validated_data.pop('strategy')
        if strategy_data["type"]!=models.StrategiesTypes.Generic:
            raise serializers.ValidationError({"type": "Strategy type is wrong"})
        strategy_instance = models.Strategies.objects.create(**strategy_data)
        sg_instance = models.StrategiesGeneric.objects.create(strategy=strategy_instance)
        sg_instance.investments.set(validated_data["investments"])
        return sg_instance
    
    def update(self, instance, validated_data):
        # Extraemos los datos de la estrategia base si están presentes
        strategy_data = validated_data.pop('strategy', None)
        # Extraemos los datos de la relación M2M 'accounts'.
        # Use None as default to check if 'accounts' was part of the update payload.
        investments_data = validated_data.pop('investments', None)
        
        if strategy_data:
            if instance.strategy.type!=strategy_data["type"]:
                raise serializers.ValidationError({"type": "You can't change strategy type"})
            # Actualizamos la instancia de Estrategia base usando su serializer
            strategy_serializer = StrategiesSerializer(instance.strategy, data=strategy_data, partial=True, context=self.context)
            strategy_serializer.is_valid(raise_exception=True)
            strategy_serializer.save()

        super().update(instance, validated_data) # This is safe if validated_data is empty after pops.

        # Actualizamos la relación M2M 'accounts'
        if investments_data is not None: # Allows clearing the relation if an empty list is passed for accounts
            instance.investments.set(investments_data)

        return instance


# Serializer para EstrategiaMarketing
class StrategiesPairsInSameAccountSerializer(serializers.HyperlinkedModelSerializer):
    # Anidamos el serializer de Estrategia para manejar los campos comunes
    strategy = StrategiesSerializer()

    class Meta:
        model = models.StrategiesPairsInSameAccount
        # Ensure 'url' (if needed, usually for HyperlinkedModelSerializer)
        # 'strategy' for the nested StrategiesSerializer
        # 'accounts' for the ManyToManyField
        fields = ['url', 'strategy', 'better_product', 'worse_product', 'account']

    def create(self, validated_data):
        # Extraemos los datos de la estrategia base
        strategy_data = validated_data.pop('strategy')

        if strategy_data["type"]!=models.StrategiesTypes.PairsInSameAccount:
            raise serializers.ValidationError({"type": "Strategy type is wrong"})
        strategy_instance = models.Strategies.objects.create(**strategy_data)
        sg_instance = models.StrategiesPairsInSameAccount.objects.create(strategy=strategy_instance, **validated_data)
        return sg_instance
    
    def update(self, instance, validated_data):
        # Extraemos los datos de la estrategia base si están presentes
        strategy_data = validated_data.pop('strategy', None)

        if strategy_data:
            if instance.strategy.type!=strategy_data["type"]:
                raise serializers.ValidationError({"type": "You can't change strategy type"})
            # Actualizamos la instancia de Estrategia base usando su serializer
            strategy_serializer = StrategiesSerializer(instance.strategy, data=strategy_data, partial=True, context=self.context)
            strategy_serializer.is_valid(raise_exception=True)
            strategy_serializer.save()

        super().update(instance, validated_data) # This is safe if validated_data is empty after pops.
        return instance

class StrategiesProductsRangeSerializer(serializers.HyperlinkedModelSerializer):
    strategy = StrategiesSerializer()

    class Meta:
        model = models.StrategiesProductsRange
        fields = ['url', 'strategy', 'product', 'investments', 'percentage_between_ranges', 'percentage_gains', 'amount', 'recomendation_method', 'only_first']


    def create(self, validated_data):
        # Extraemos los datos de la estrategia base
        strategy_data = validated_data.pop('strategy')
        investments=validated_data.pop('investments')

        if strategy_data["type"]!=models.StrategiesTypes.Ranges:
            raise serializers.ValidationError({"type": "Strategy type is wrong"})
        strategy_instance = models.Strategies.objects.create(**strategy_data)
        sg_instance = models.StrategiesProductsRange.objects.create(strategy=strategy_instance, **validated_data)
        sg_instance.investments.set(investments)
        return sg_instance
    
    def update(self, instance, validated_data):
        # Extraemos los datos de la estrategia base si están presentes
        strategy_data = validated_data.pop('strategy', None)
        investments_data = validated_data.pop('investments', None)

        if strategy_data:
            if instance.strategy.type!=strategy_data["type"]:
                raise serializers.ValidationError({"type": "You can't change strategy type"})
            # Actualizamos la instancia de Estrategia base usando su serializer
            strategy_serializer = StrategiesSerializer(instance.strategy, data=strategy_data, partial=True, context=self.context)
            strategy_serializer.is_valid(raise_exception=True)
            strategy_serializer.save()

        super().update(instance, validated_data) # This is safe if validated_data is empty after pops.
        # Actualizamos la relación M2M 'accounts'
        if investments_data is not None: # Allows clearing the relation if an empty list is passed for accounts
            instance.investments.set(investments_data)
        return instance


# Serializer para la vista de detalle que combina todas las estrategias
class NewStrategyDetailedSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Strategies
        fields = ('url', 'id')
        
    def to_representation(self, instance):
        # Reescribe la representación para coincidir con los Serializer dependiendo de su type
        if instance.type==models.StrategiesTypes.FastOperations:
            return StrategiesFastOperationsSerializer(instance.strategiesfastoperations, context=self.context).data

        elif instance.type==models.StrategiesTypes.Generic:
            return StrategiesGenericSerializer(instance.strategiesgeneric, context=self.context).data

        elif instance.type==models.StrategiesTypes.PairsInSameAccount:
            return StrategiesPairsInSameAccountSerializer(instance.strategiespairsinsameaccount, context=self.context).data

        elif instance.type==models.StrategiesTypes.Ranges:
            return StrategiesProductsRangeSerializer(instance.strategiesproductsrange, context=self.context).data


class FastOperationsCoverageSerializer(serializers.HyperlinkedModelSerializer):
    currency= serializers.SerializerMethodField()
    class Meta:
        model = models.FastOperationsCoverage
        fields = ('url', 'id', 'datetime', 'investments', 'amount','comment', 'currency')

    def get_currency(self, o):
        return o.investments.products.currency
        



@extend_schema_serializer(
    component_name="IOSRequest", 
    examples = [
         OpenApiExample(
            'from_ids',
            summary='from_ids',
            description='from_ids description',
            value={
                'classmethod_str': "from_ids",
                'datetime': "2019-01-01T12:12:12Z", 
                'mode':1, 
                'simulation': [], 
                'investments': [1, 2, 3]
            },
            request_only=True, # signal that example only applies to requests
        ),
         OpenApiExample(
            'from_all',
            summary='from_all summary',
            description='from_all description',
            value={
                'classmethod_str': "from_all",
                'datetime': "2019-01-01T12:12:12Z", 
                'mode':1, 
                'simulation': [], 
            },
            request_only=True, # signal that example only applies to requests
        ),
    ]
)
class IOSRequestSerializer(serializers.Serializer):
    classmethod_str = serializers.CharField(max_length=200)
    datetime=serializers.DateTimeField()
    mode= serializers.IntegerField()
    simulation=InvestmentsoperationsSerializer(many=True)
    investments = serializers.ListField(child = serializers.IntegerField())


class ProductsStrategiesSerializer(serializers.HyperlinkedModelSerializer):
    localname = serializers.SerializerMethodField()
    class Meta:
        model = models.ProductsStrategies
        fields = ('url', 'id', 'name', 'localname')
    @extend_schema_field(OpenApiTypes.STR)
    def get_localname(self, obj):
        return  _(obj.name)
