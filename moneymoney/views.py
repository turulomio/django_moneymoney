from base64 import  b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management import call_command
from django.db import transaction, connection, reset_queries
from django.db.models import prefetch_related_objects, Count, Sum, Q, Max, Subquery
from django.db.models.functions.datetime import ExtractMonth, ExtractYear
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from itertools import permutations
from math import ceil
from moneymoney import models, serializers, ios, functions
from moneymoney.types import eConcept, eProductType, eOperationType, eProductStrategy
from moneymoney.reusing.decorators import ptimeit
from pydicts.percentage import Percentage,  percentage_between
from request_casting.request_casting import RequestBool, RequestDate, RequestDecimal, RequestDtaware, RequestUrl, RequestString, RequestInteger, RequestListOfIntegers, RequestListOfUrls, all_args_are_not_none
from statistics import median
from subprocess import run
from pydicts import lod, lod_ymv, casts, myjsonencoder
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status, serializers as drf_serializers
from rest_framework.views import APIView
from zoneinfo import available_timezones
from tempfile import TemporaryDirectory

ptimeit
reset_queries


class GroupCatalogManager(permissions.BasePermission):
    """Permiso que comprueba si pertenece al grupo CatalogManager """
    def has_permission(self, request, view):
        return request.user.groups.filter(name="CatalogManager").exists()


class CatalogModelViewSet(viewsets.ModelViewSet):
    def get_permissions(self):    
        """
            Overrides get_permissions to set GroupCatalogManager permission for CRUD actions
            Only list and get actions authenticated, ther rest for GroupCatalogManager.
        """
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            self.permission_classes = [permissions.IsAuthenticated, GroupCatalogManager]
        else:# get and custome actions
            self.permission_classes = [permissions.IsAuthenticated]
        return viewsets.ModelViewSet.get_permissions(self)



@permission_classes([permissions.IsAuthenticated, ])
@api_view(['GET', ])
def CatalogManager(request):
    return JsonResponse( request.user.groups.filter(name="CatalogManager").exists(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class ConceptsViewSet(viewsets.ModelViewSet):
    queryset = models.Concepts.objects.all()
    serializer_class = serializers.ConceptsSerializer
    permission_classes = [permissions.IsAuthenticated]  

    @action(detail=False, methods=["get"], name='Concepts list with use and migration information', url_path="used", url_name='used', permission_classes=[permissions.IsAuthenticated])
    def used(self, request):
        qs=models.Concepts.objects.all() 
        r=[]
        for o in qs:
            r.append({
                "id": o.id, 
                "name": o.name, 
                "url": request.build_absolute_uri(reverse('concepts-detail', args=(o.pk, ))), 
                "localname": _(o.name), 
                "editable": o.editable, 
                "used": o.get_used(), 
                "operationstypes": request.build_absolute_uri(reverse('operationstypes-detail', args=(o.operationstypes.pk, ))), 
                "migrable": o.is_migrable(), 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        

    @extend_schema(
        request=inline_serializer(
           name='ConceptsDataTransfer',
           fields={
               'to': drf_serializers.CharField(),
           }
       ), 
        description="Makes a IOS object", 
    )
    @action(detail=True, methods=['POST'], name='Transfer data from a concept to other', url_path="data_transfer", url_name='data_transfer', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def data_transfer(self, request, pk=None):
        concept_to=RequestUrl(request, "to", models.Concepts)
        if concept_to is not None:
            concept_from=self.get_object()
            models.Accountsoperations.objects.filter(concepts=concept_from).update(concepts=concept_to)
            models.Creditcardsoperations.objects.filter(concepts=concept_from).update(concepts=concept_to)
            models.Dividends.objects.filter(concepts=concept_from).update(concepts=concept_to)
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["get"], name='Returns historical concept report', url_path="historical_report", url_name='historical_report', permission_classes=[permissions.IsAuthenticated])
    def historical_report(self, request, pk=None):
        concept= self.get_object()
        r={}
        json_concepts_historical=[]
        with connection.cursor() as c:
            c.execute("""
        select date_part('year',datetime)::int as year,  date_part('month',datetime)::int as month, sum(amount) as value 
        from ( 
                    SELECT accountsoperations.datetime, accountsoperations.concepts_id,  accountsoperations.amount  FROM accountsoperations where concepts_id=%s 
                        UNION ALL 
                    SELECT creditcardsoperations.datetime, creditcardsoperations.concepts_id, creditcardsoperations.amount FROM creditcardsoperations where concepts_id=%s
                ) as uni 
        group by date_part('year',datetime), date_part('month',datetime) order by 1,2 ;
        """, [concept.id, concept.id])
            rows=functions.dictfetchall(c)

        if len(rows)==0:
            return JsonResponse( {"data":[], "total":0, "median":0, "average":0}, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
            
        firstyear=int(rows[0]['year'])
        # Create all data spaces filling year
        for year in range(firstyear, date.today().year+1):
            json_concepts_historical.append({"year": year, "m1":0, "m2":0, "m3":0, "m4":0, "m5":0, "m6":0, "m7":0, "m8":0, "m9":0, "m10":0, "m11":0, "m12":0, "total":0})
        # Fills spaces with values
        for row in rows:
            j_row=json_concepts_historical[row['year']-firstyear]
            j_row[f"m{row['month']}"]=float(row['value'])
        
        for d in json_concepts_historical:
            d["total"]=d["m1"]+d["m2"]+d["m3"]+d["m4"]+d["m5"]+d["m6"]+d["m7"]+d["m8"]+d["m9"]+d["m10"]+d["m11"]+d["m12"]

        r["data"]=json_concepts_historical
        r["total"]=lod.lod_sum(json_concepts_historical, "total")
        r["median"]=lod.lod_median(rows, 'value')
        r["average"]=lod.lod_average(rows, 'value')
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

    @action(detail=True, methods=["get"], name='Returns historical concept report detail', url_path="historical_report_detail", url_name='historical_report_detail', permission_classes=[permissions.IsAuthenticated])
    def ReportConceptsHistoricalDetail(self, request, pk=None):
        concept= self.get_object()
        year=RequestInteger(request, "year")
        month=RequestInteger(request, "month")
        if all_args_are_not_none(concept, year, month) is False:
            return Response({'status': 'year,month or concept is None'}, status=status.HTTP_400_BAD_REQUEST)
    
        qs_ao=models.Accountsoperations.objects.filter(concepts=concept, datetime__year=year, datetime__month=month)
        qs_cco=models.Creditcardsoperations.objects.filter(concepts=concept, datetime__year=year, datetime__month=month)
        
        data={
            "ao":  serializers.AccountsoperationsSerializer(qs_ao, many=True, context={'request': request}).data, 
            "cco":  serializers.CreditcardsoperationsSerializer(qs_cco, many=True, context={'request': request}).data, 
        }        
        return JsonResponse( data, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class CreditcardsViewSet(viewsets.ModelViewSet):
    queryset = models.Creditcards.objects.select_related("accounts").all()
    serializer_class = serializers.CreditcardsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    def queryset_for_list_methods(self):
        active=RequestBool(self.request, 'active')
        account_id=RequestInteger(self.request, 'account')
        if active is not None:
            self.queryset=self.queryset.filter(active=active)
        if account_id is not None:
            self.queryset= self.queryset.filter(accounts_id=account_id)
        return self.queryset.order_by("name")
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=False, type=bool), 
            OpenApiParameter(name='account', description='Filter by account', required=False, type=OpenApiTypes.URI), 
        ],
    )
    def list(self, request):
        serializer = serializers.CreditcardsSerializer(self.queryset_for_list_methods(), many=True, context={'request': request})
        return Response(serializer.data)
        
    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=False, type=bool), 
            OpenApiParameter(name='account', description='Filter by account', required=False, type=OpenApiTypes.URI), 
        ],
    )
    @action(detail=False, methods=["get"], name='List creditcards with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):    
        r=[]
        for o in self.queryset_for_list_methods():
            if o.deferred==False:
                balance=0
            else:
                balance=models.Creditcardsoperations.objects.filter(creditcards_id=o.id, paid=False).aggregate(Sum("amount"))["amount__sum"] or 0 #Puede ser None, en ese caso devuelve 0
            r.append({
                "id": o.id,  
                "url": request.build_absolute_uri(reverse('creditcards-detail', args=(o.pk, ))), 
                "name":o.name, 
                "number": o.number, 
                "deferred": o.deferred, 
                "active": o.active, 
                "maximumbalance": o.maximumbalance, 
                "balance": balance, 
                "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.pk, ))), 
                "account_currency": o.accounts.currency, 
                "is_deletable": o.is_deletable()
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

    @action(detail=True, methods=['GET'], name='Obtain historical payments of a credit card', url_path="payments", url_name='payments', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def payments(self, request, pk=None):
        creditcard=self.get_object()
        lod_=list(models.Creditcardsoperations.objects.filter(
            creditcards=creditcard, 
            accountsoperations__concepts__id=eConcept.CreditCardBilling, 
        ).order_by("accountsoperations__datetime").values(
            "accountsoperations__id", 
            "accountsoperations__amount", 
            "accountsoperations__datetime"
        ).annotate(count=Count("id")))
        lod.lod_rename_key(lod_, "accountsoperations__id", "accountsoperations_id")
        lod.lod_rename_key(lod_, "accountsoperations__amount", "amount")
        lod.lod_rename_key(lod_, "accountsoperations__datetime", "datetime")
        return JsonResponse( lod_, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        


    @action(detail=True, methods=['POST'], name='Pay cco of a credit card', url_path="pay", url_name='pay', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def pay(self, request, pk=None):
        creditcard=self.get_object()
        dt_payment=RequestDtaware(request, "dt_payment", request.user.profile.zone)
        cco_ids=RequestListOfIntegers(request, "cco")
        
        if dt_payment is not None and cco_ids is not None:
            qs_cco=models.Creditcardsoperations.objects.all().filter(pk__in=(cco_ids))
            sumamount=0
            for o in qs_cco:
                sumamount=sumamount+o.amount
            
            c=models.Accountsoperations()
            c.datetime=dt_payment
            c.concepts=models.Concepts.objects.get(pk=eConcept.CreditCardBilling)
            c.amount=sumamount
            c.accounts=creditcard.accounts
            c.comment=""
            c.save()

            #Modifica el registro y lo pone como paid y la datetime de pago y añade la opercuenta
            for o in qs_cco:
                o.paid_datetime=dt_payment
                o.paid=True
                o.accountsoperations_id=c.id
                o.save()
            serializer = serializers.AccountsoperationsSerializer(c, many=False, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    

    

    @action(detail=True, methods=['GET'], name='Get a list of creditcards operations with balance', url_path="operationswithbalance", url_name='operationswithbalance', permission_classes=[permissions.IsAuthenticated])
    def operationswithbalance(self, request, pk=None):   
        creditcard=self.get_object()
        paid=RequestBool(request, 'paid')
        accountsoperations_id=RequestInteger(request, "accountsoperations_id")

        if paid is None and accountsoperations_id is None:
            return Response(_("Paid or accountsoperations_id can't be None at the same time"), status=status.HTTP_400_BAD_REQUEST)
            
        qs=models.Creditcardsoperations.objects.select_related("creditcards", "concepts", "creditcards__accounts").all()
        if paid is not None:
            qs=qs.filter(paid=paid, creditcards=creditcard).order_by("datetime")
        if accountsoperations_id is not None:
            qs=qs.filter(accountsoperations__id=accountsoperations_id).order_by("datetime")

        balance=0
        r=[]
        for o in qs:
            
            balance=balance+o.amount
            r.append({
                "id": o.id,  
                "url": request.build_absolute_uri(reverse('creditcardsoperations-detail', args=(o.pk, ))), 
                "datetime":o.datetime, 
                "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(o.concepts.pk, ))), 
                "amount": o.amount, 
                "balance":  balance, 
                "comment": o.comment, 
                "creditcards":request.build_absolute_uri(reverse('creditcards-detail', args=(o.creditcards.pk, ))), 
                "paid": o.paid, 
                "paid_datetime": o.paid_datetime, 
                "currency": o.creditcards.accounts.currency, 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)



class CreditcardsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Creditcardsoperations.objects.all().select_related("creditcards").select_related("creditcards__accounts")
    serializer_class = serializers.CreditcardsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  

    
class Derivatives(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        description="Return 'Derivatives and Fast InvestmentOperations' accounts operations. Also Balance with FastOperationsCoverage", 
    )
    def get(self, request, *args, **kwargs):
        r={}
        qs=models.Accountsoperations.objects.filter(concepts__id__in=(
            eConcept.DerivativesAdjustment, 
            eConcept.DerivativesCommission, 
            eConcept.DerivativesSwap, 
            eConcept.FastInvestmentOperations
            ))\
            .annotate(year=ExtractYear('datetime'), month=ExtractMonth('datetime'))\
            .values( 'year', 'month')\
            .annotate(amount=Sum('amount'))\
            .order_by('year', 'month')
            
        r["derivatives"]=lod_ymv.lod_ymv_transposition(list(qs.values('year', 'month', 'amount')), key_value="amount")
        
        qs_coverage=models.FastOperationsCoverage.objects.all()\
            .annotate(year=ExtractYear('datetime'), month=ExtractMonth('datetime'))\
            .values( 'year', 'month')\
            .annotate(amount=Sum('amount'))\
            .order_by('year', 'month')
            
        lymv_coverage=lod_ymv.lod_ymv_transposition(list(qs_coverage.values('year', 'month', 'amount')), key_value="amount")
            
        r["balance"]=lod_ymv.lod_ymv_transposition_sum(r["derivatives"], lymv_coverage)
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)        

class DividendsViewSet(viewsets.ModelViewSet):
    queryset = models.Dividends.objects.all().select_related("investments", "investments__accounts")
    serializer_class = serializers.DividendsSerializer
    permission_classes = [permissions.IsAuthenticated] 
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='investments[]', description='Filter by investments', required=False, type=OpenApiTypes.OBJECT), 
            OpenApiParameter(name='datetime', description='Filter by datetime from', required=False, type=OpenApiTypes.DATETIME), 
        ],
    )
    def list(self, request):       
        investments_ids=RequestListOfIntegers(self.request,"investments[]", []) 
        datetime=RequestDtaware(self.request, 'from', self.request.user.profile.zone)
        if len(investments_ids)>0 and datetime is None:
            self.queryset=self.queryset.filter(investments__in=investments_ids).order_by("datetime")
        elif len(investments_ids)>0 and datetime is not None:
            self.queryset=self.queryset.filter(investments__in=investments_ids,  datetime__gte=datetime).order_by("datetime")
        else:
            self.queryset=self.queryset.order_by("datetime")
        serializer = serializers.DividendsSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)

class DpsViewSet(viewsets.ModelViewSet):
    queryset = models.Dps.objects.all()
    serializer_class = serializers.DpsSerializer
    permission_classes = [permissions.IsAuthenticated]      

    @extend_schema(
        parameters=[
            OpenApiParameter(name='product', description='Filter by product', required=False, type=OpenApiTypes.URI), 
        ],
    )
    def list(self, request):
        product=RequestUrl(self.request, 'product', models.Products)
        if all_args_are_not_none(product):
            self.queryset=self.queryset.filter(products=product)
        serializer = serializers.DpsSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)

class OrdersViewSet(viewsets.ModelViewSet):
    queryset = models.Orders.objects.select_related("investments","investments__accounts","investments__products","investments__products__productstypes","investments__products__leverages").all()
    serializer_class = serializers.OrdersSerializer
    permission_classes = [permissions.IsAuthenticated]  


    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter actives', required=False, type=OpenApiTypes.BOOL),  
            OpenApiParameter(name='expired', description='Filter expired orders', required=False, type=OpenApiTypes.BOOL), 
            OpenApiParameter(name='expired_days', description='Filter expired days', required=False, type=OpenApiTypes.INT), 
            OpenApiParameter(name='executed', description='Filter executed', required=False, type=OpenApiTypes.BOOL), 

],
    )
    def list(self, request):
        active=RequestBool(self.request, 'active')
        expired=RequestBool(self.request, 'expired')
        expired_days=RequestInteger(self.request, 'expired_days')
        executed=RequestBool(self.request, 'executed')
        if active is not None:
            self.queryset=self.queryset.filter(Q(expiration__gte=date.today()) | Q(expiration__isnull=True), executed__isnull=True)
        elif expired is not None:
            self.queryset=self.queryset.filter(expiration__lte=date.today(),  executed__isnull=True)
        elif expired_days is not None:
            """
                Returns orders that have expired in last expired_days and that haven't been reordered. Used to alert expired orders
            """
            qs_orders_expired_days=self.queryset.filter(expiration__range=(date.today()-timedelta(days=expired_days), date.today()),  executed__isnull=True)

            set_investments_with_orders_active=set(models.Orders.objects.filter(Q(expiration__gte=date.today()) | Q(expiration__isnull=True), executed__isnull=True).values_list("investments_id", flat=True))
            set_investments_with_orders_expired_days=set(qs_orders_expired_days.values_list("investments_id", flat=True))
            set_investments_with_orders_not_reorderd=set_investments_with_orders_expired_days-set_investments_with_orders_active
            self.queryset=qs_orders_expired_days.filter(investments_id__in=list(set_investments_with_orders_not_reorderd))
        elif executed is not None:
            self.queryset=self.queryset.filter(executed__isnull=False)        
        
        r=[]
        for o in self.queryset:
            r.append({
                "id": o.id,  
                "url": request.build_absolute_uri(reverse('orders-detail', args=(o.pk, ))), 
                "date":o.date, 
                "expiration": o.expiration, 
                "investments": request.build_absolute_uri(reverse('investments-detail', args=(o.investments.pk, ))), 
                "products": request.build_absolute_uri(reverse('products-detail', args=(o.investments.products.pk, ))), 
                "investmentsname":o.investments.fullName(), 
                "currency": o.investments.products.currency, 
                "shares": o.shares, 
                "price": o.price, 
                "amount": o.shares*o.price*o.investments.products.real_leveraged_multiplier(), 
                "percentage_from_price": percentage_between(o.investments.products.basic_results()["last"], o.price),
                "executed": o.executed,  
                "current_price": o.investments.products.basic_results()["last"], 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class OperationstypesViewSet(CatalogModelViewSet):
    queryset = models.Operationstypes.objects.all()
    serializer_class = serializers.OperationstypesSerializer



class StrategiesViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]  
    queryset = models.Strategies.objects.all()
    http_method_names = ['get', 'head', 'options']
    
    def get_serializer_class(self):
        return serializers.NewStrategyDetailedSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=True, type=bool), 
            OpenApiParameter(name='type', description='Filter by type', required=True, type=int), 
        ],
    )
    def list(self, request):
        active=RequestBool(request, "active")
        type=RequestInteger(request, "type")
        if all_args_are_not_none(active, type):
            self.queryset=self.queryset.filter(dt_to__isnull=active, type=type)
        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], name='List strategies with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request): 
        active=RequestBool(request, 'active')
        if active is None:
            qs=models.Strategies.objects.all()
        else:
            if active is True:
                qs=models.Strategies.objects.filter(dt_to__isnull=True)
            else:
                qs=models.Strategies.objects.filter(dt_to__isnull=False)

        r=[]
        for strategy in qs:
            if strategy.type==models.StrategiesTypes.FastOperations:
                invested=models.Accounts.accounts_balance(strategy.strategiesfastoperations.accounts.all(),strategy.dt_from,request.user.profile.currency)["balance_user_currency"]
                qs_ao=models.Accountsoperations.objects.filter(accounts_id__in=functions.qs_to_ids(strategy.strategiesfastoperations.accounts.all()), concepts_id=eConcept.FastInvestmentOperations, datetime__gte=strategy.dt_from).select_related("accounts")
                gains_current_net_user=qs_ao.aggregate(Sum("amount"))["amount__sum"] or 0
                gains_historical_net_user=0
                sum_dividends_net_user=0

            elif strategy.type==models.StrategiesTypes.Generic:                
                plio=ios.IOS.from_qs(timezone.now(), request.user.profile.currency, strategy.strategiesgeneric.investments.all(), 1)
                invested=plio.sum_total_io_current()["invested_user"]
                gains_current_net_user=plio.sum_total_io_current()["gains_net_user"]
                gains_historical_net_user=plio.io_historical_sum_between_dt(strategy.dt_from, strategy.dt_to_for_comparations(),  "gains_net_user")
                lod_dividends_net_user=models.Dividends.lod_ym_netgains_dividends(request, ids=functions.qs_to_ids(strategy.strategiesgeneric.investments.all()),  dt_from=strategy.dt_from, dt_to=strategy.dt_to_for_comparations())
                sum_dividends_net_user=lod.lod_sum(lod_dividends_net_user, "total")
            elif strategy.type==models.StrategiesTypes.Ranges:                
                plio=ios.IOS.from_qs(timezone.now(), request.user.profile.currency, strategy.strategiesproductsrange.investments.all(), 1)
                invested=plio.sum_total_io_current()["invested_user"]
                gains_current_net_user=plio.sum_total_io_current()["gains_net_user"]
                gains_historical_net_user=plio.io_historical_sum_between_dt(strategy.dt_from, strategy.dt_to_for_comparations(),  "gains_net_user")
                lod_dividends_net_user=models.Dividends.lod_ym_netgains_dividends(request, ids=functions.qs_to_ids(strategy.strategiesproductsrange.investments.all()),  dt_from=strategy.dt_from, dt_to=strategy.dt_to_for_comparations())
                sum_dividends_net_user=lod.lod_sum(lod_dividends_net_user, "total")

            elif strategy.type==models.StrategiesTypes.PairsInSameAccount:                
                invested=models.Accounts.accounts_balance(models.Accounts.objects.filter(id=strategy.strategiespairsinsameaccount.account.id),strategy.dt_from,request.user.profile.currency)["balance_user_currency"]
                qs_ao=models.Accountsoperations.objects.filter(accounts=strategy.strategiespairsinsameaccount.account, concepts_id=eConcept.FastInvestmentOperations, datetime__gte=strategy.dt_from).select_related("accounts")
                gains_current_net_user=qs_ao.aggregate(Sum("amount"))["amount__sum"] or 0
                gains_historical_net_user=0
                sum_dividends_net_user=0
            
            d_balance={
                "invested":invested,
                "gains_current_net_user":  gains_current_net_user,  
                "gains_historical_net_user": gains_historical_net_user, 
                "dividends_net_user": sum_dividends_net_user, 
                "total_net_user":gains_current_net_user + gains_historical_net_user + sum_dividends_net_user, 
            }
            d_strategy=serializers.NewStrategyDetailedSerializer(instance=strategy , context={'request': request}).data
            d_strategy["balance"]=d_balance
            r.append(d_strategy)
        return Response(r)




class StrategiesFastOperationsViewSet(viewsets.ModelViewSet):
    queryset = models.StrategiesFastOperations.objects.all()
    serializer_class = serializers.StrategiesFastOperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  

    
    @action(detail=True, methods=["get"], name='Gets a detail of a fast operations strategy. Returns a list of account operations with fast operations', url_path="detailed", url_name='detailed', permission_classes=[permissions.IsAuthenticated])
    def detailed(self, request, pk=None): 
        strategy_fos=self.get_object()
        if strategy_fos is not None:
            qs_ao=models.Accountsoperations.objects.filter(accounts_id__in=functions.qs_to_ids(strategy_fos.accounts.all()), concepts_id=eConcept.FastInvestmentOperations, datetime__gte=strategy_fos.strategy.dt_from).select_related("accounts")
            serializer = serializers.AccountsoperationsSerializer(qs_ao, many=True, context={'request': request})
            return Response(serializer.data)
        return Response({'status': _('Fast operations strategy was not found')}, status=status.HTTP_404_NOT_FOUND)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.strategy.delete()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class StrategiesPairsInSameAccountViewSet(viewsets.ModelViewSet):
    queryset = models.StrategiesPairsInSameAccount.objects.all()
    serializer_class = serializers.StrategiesPairsInSameAccountSerializer
    permission_classes = [permissions.IsAuthenticated]  

    
    @action(detail=True, methods=["get"], name='Gets a detail of a pairs in same account strategy', url_path="detailed", url_name='detailed', permission_classes=[permissions.IsAuthenticated])
    def detailed(self, request, pk=None): 
        # strategy_fos=self.get_object()
        # if strategy_fos is not None:
        #     qs_ao=models.Accountsoperations.objects.filter(accounts_id__in=functions.qs_to_ids(strategy_fos.accounts.all()), concepts_id=eConcept.FastInvestmentOperations, datetime__gte=strategy_fos.strategy.dt_from).select_related("accounts")
        #     serializer = serializers.AccountsoperationsSerializer(qs_ao, many=True, context={'request': request})
        #     return Response(serializer.data)
        return Response({'status': _('Not developed yet')}, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.strategy.delete()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)    
class StrategiesProductsRangeViewSet(viewsets.ModelViewSet):
    queryset = models.StrategiesProductsRange.objects.all()
    serializer_class = serializers.StrategiesProductsRangeSerializer
    permission_classes = [permissions.IsAuthenticated]  

    
    @action(detail=True, methods=["get"], name='Gets a detail of a pairs in same account strategy', url_path="detailed", url_name='detailed', permission_classes=[permissions.IsAuthenticated])
    def detailed(self, request, pk=None): 
        strategy=self.get_object()
        if strategy is not None:
            ios_=ios.IOS.from_qs_merging_io_current(timezone.now(), request.user.profile.currency, strategy.investments.all(), ios.IOSModes.ios_totals_sumtotals)
            return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,  safe=False)
        return Response({'status': _('Strategy was not found')}, status=status.HTTP_404_NOT_FOUND)
    

            
    # @action(detail=True, methods=["get"], name='Gets a IOS from a strategy', url_path="ios", url_name='ios', permission_classes=[permissions.IsAuthenticated])
    # def ios(self, request, pk=None): 
    #     strategy=self.get_object()
    #     if strategy is not None:
    #         ios_=ios.IOS.from_qs_merging_io_current(timezone.now(), request.user.profile.currency, strategy.investments.all(), ios.IOSModes.ios_totals_sumtotals)
    #         return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,  safe=False)
    #     return Response({'status': _('Strategy was not found')}, status=status.HTTP_404_NOT_FOUND)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.strategy.delete()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class StrategiesGenericViewSet(viewsets.ModelViewSet):
    queryset = models.StrategiesGeneric.objects.all()
    serializer_class = serializers.StrategiesGenericSerializer
    permission_classes = [permissions.IsAuthenticated]  

    @action(detail=True, methods=["get"], name='Gets a IOS from a strategy', url_path="detailed", url_name='detailed', permission_classes=[permissions.IsAuthenticated])
    def detailed(self, request, pk=None): 
        strategy=self.get_object()
        if strategy is not None:
            ios_=ios.IOS.from_qs_merging_io_current(timezone.now(), request.user.profile.currency, strategy.investments.all(), ios.IOSModes.ios_totals_sumtotals)
            return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,  safe=False)
        return Response({'status': _('Generic strategy was not found')}, status=status.HTTP_404_NOT_FOUND)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.strategy.delete()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class InvestmentsClasses(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        description="Returns data to generate investments classes in pies", 
        request=None, 
        responses=OpenApiTypes.OBJECT
    )

    def get(self, request, *args, **kwargs):
        def json_classes_by_pci():
            ld=[]
            for product_strategy in models.ProductsStrategies.objects.all():
                d={"name": product_strategy.name, "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if investment.products.productsstrategies.id==product_strategy.id:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                if product_strategy.id==eProductStrategy.Call:
                    d["balance"]=d["balance"]+accounts_balance
                    d["invested"]=d["invested"]+accounts_balance
                ld.append(d)
            return ld

        def json_classes_by_product():
            ld=[]
            for product in models.Products.qs_distinct_with_investments(only_active=True):
                d={"name": product.fullName(), "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if investment.products==product:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                ld.append(d)
            ld.append({"name": "Accounts", "balance": accounts_balance,  "invested": accounts_balance})
            return ld

        def json_classes_by_percentage():
            ld=[]
            for percentage in range(0, 11):
                d={"name": f"{percentage*10}% variable", "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if ceil(investment.products.percentage/10.0)==percentage:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                if percentage==0:
                    d["balance"]=d["balance"]+accounts_balance
                    d["invested"]=d["invested"]+accounts_balance
                ld.append(d)
            return ld

        def json_classes_by_producttype():
            ld=[]
            for producttype in models.Productstypes.objects.all():
                d={"name": producttype.name, "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if investment.products.productstypes==producttype:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                if producttype.id==11:#Accounts
                    d["balance"]=d["balance"]+accounts_balance
                    d["invested"]=d["invested"]+accounts_balance
                ld.append(d)
            return ld
            
        def json_classes_by_leverage():
            ld=[]
            for leverage in models.Leverages.objects.all():
                d={"name": leverage.name, "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if investment.products.leverages==leverage:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                if leverage.id==1:#Accounts
                    d["balance"]=d["balance"]+accounts_balance
                    d["invested"]=d["invested"]+accounts_balance
                ld.append(d)
            return ld
            
        ###################
        accounts_balance=models.Accounts.accounts_balance(models.Accounts.objects.filter(active=True), timezone.now(), 'EUR')["balance_user_currency"]
        qs_investments_active=models.Investments.objects.filter(active=True).select_related("products","products__productstypes","accounts","products__leverages")

        plio=ios.IOS.from_qs(timezone.now(), request.user.profile.currency, qs_investments_active,  1)

        d={}
        d["by_leverage"]=json_classes_by_leverage()
        d["by_pci"]=json_classes_by_pci()
        d["by_percentage"]=json_classes_by_percentage()
        d["by_product"]=json_classes_by_product()
        d["by_producttype"]=json_classes_by_producttype()
        
        return JsonResponse( d, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

class Alerts(APIView):
    permission_classes = [permissions.IsAuthenticated]    
    @extend_schema(
        description="Returns alerts from the application", 
        request=None, 
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Response",
                        value={
                          "server_time": "2023-08-01T03:55:29.122943+00:00",
                          "expired_days": 7,
                          "orders_expired": [],
                          "banks_inactive_with_balance": [],
                          "accounts_inactive_with_balance": [],
                          "investments_inactive_with_balance": []
                        },
                        response_only=True,
                    )
                ],
            )
        }, 
    )
    def get(self, request, *args, **kwargs):
        r={}
        r["server_time"]=timezone.now()
        
        #Expired orders calling other viewset from this viewsets
        r["expired_days"]=7
        r["orders_expired"]=functions.internal_modelviewset_request(OrdersViewSet, "list", {"expired_days":r["expired_days"]}, params_method="GET", user=request.user)
        
        # Get all inactive banks with balance
        r["banks_inactive_with_balance"]=[]
        lod_banks=functions.internal_modelviewset_request(BanksViewSet, "withbalance", {"active":False},  params_method="GET", user=request.user)
        for d in lod_banks:
            if d["balance_total"]!=0:
                r["banks_inactive_with_balance"].append(d)


        # Get all inactive accounts status
        r["accounts_inactive_with_balance"]=[]
        lod_accounts=functions.internal_modelviewset_request(AccountsViewSet, "withbalance", {"active":False},  params_method="GET", user=request.user)
        for d in lod_accounts:
            if d["balance_account"]!=0:
                r["accounts_inactive_with_balance"].append(d)

        # Get all investments status
        r["investments_inactive_with_balance"]=[]
        qs=models.Investments.objects.filter(active=False)
        plio_inactive=ios.IOS.from_qs(timezone.now(), request.user.profile.currency, qs,  2)
        for id in plio_inactive.entries():
            plio=plio_inactive.d(id)
            if plio["total_io_current"]["balance_investment"]!=0:
                r["investments_inactive_with_balance"].append(plio)
        
        functions.show_queries_function()
        return JsonResponse(r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class Timezones(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(request=None, responses=OpenApiTypes.STR)
    def get(self, request, *args, **kwargs):
        r=list(available_timezones())
        r.sort()
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)


class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = models.Investments.objects.all().select_related("accounts")
    serializer_class = serializers.InvestmentsSerializer
    permission_classes = [permissions.IsAuthenticated]  
        
    def queryset_for_list_methods(self,request):
        active=RequestBool(request, "active")
        bank_id=RequestInteger(request,"bank")
        self.queryset=self.get_queryset()
        if bank_id is not None:
            self.queryset=self.queryset.filter(accounts__banks__id=bank_id,  active=True)
        elif active is not None:
            self.queryset=self.queryset.filter(active=active)
        return self.queryset
    
    
    def list(self, request):
        """
            It's better to ovverride list than get_queryset due to active is a class_attribute, and list only is for list and queryset for all methods
        """

        serializer = self.get_serializer(self.queryset_for_list_methods(request), many=True)
        return Response(serializer.data)
            
    
    @action(detail=False, methods=["get"], name='List investments with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request): 
        def percentage_to_selling_point(shares, selling_price, last_quote):       
            """Función que calcula el tpc selling_price partiendo de las el last y el valor_venta
            Necesita haber cargado mq getbasic y operinversionesactual"""
            if selling_price==0 or selling_price==None or last_quote is None:
                return Percentage()
            if shares>0:
                return Percentage(selling_price-last_quote, last_quote)
            else:#Long short products
                return Percentage(-(selling_price-last_quote), last_quote)
        #######################################      
        active=RequestBool(request, "active")
        if active is None:        
            return Response(_('You must set active parameter'), status=status.HTTP_400_BAD_REQUEST)
            
        qs_investments=self.queryset_for_list_methods(request).select_related("accounts",  "products", "products__productstypes","products__stockmarkets",  "products__leverages")
        plio=ios.IOS.from_qs(timezone.now(), 'EUR', qs_investments,  mode=2)
        r=[]
        for o in qs_investments:
            percentage_invested=None if plio.d_total_io_current(o.id)["invested_user"]==0 else  plio.d_total_io_current(o.id)["gains_gross_user"]/plio.d_total_io_current(o.id)["invested_user"]
            try:                
                last_day_diff= (plio.d_basic_results(o.id)["last"]-plio.d_basic_results(o.id)["penultimate"])*plio.d_total_io_current(o.id)["shares"]*o.products.real_leveraged_multiplier()
            except:
                last_day_diff=0

            r.append({
                "id": o.id,  
                "name":o.name, 
                "fullname":o.fullName(), 
                "active":o.active, 
                "url":request.build_absolute_uri(reverse('investments-detail', args=(o.pk, ))), 
                "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.id, ))), 
                "products":request.build_absolute_uri(reverse('products-detail', args=(o.products.id, ))), 
                "last_datetime": None if plio.d_basic_results(o.id)["last"] is None else plio.d_basic_results(o.id)["last_datetime"], 
                "last": plio.d_basic_results(o.id)["last"], 
                "daily_difference": last_day_diff, 
                "daily_percentage": None if plio.d_basic_results(o.id)["penultimate"] is None or plio.d_basic_results(o.id)["last"] is None else percentage_between(plio.d_basic_results(o.id)["penultimate"], plio.d_basic_results(o.id)["last"]), 
                "invested_user": plio.d_total_io_current(o.id)["invested_user"], 
                "gains_user": plio.d_total_io_current(o.id)["gains_gross_user"], 
                "balance_user": plio.d_total_io_current(o.id)["balance_user"], 
                "currency": o.products.currency, 
                "currency_account": o.accounts.currency, 
                "percentage_invested": percentage_invested, 
                "percentage_selling_point": None if plio.d_basic_results(o.id)["last"] is None else percentage_to_selling_point(plio.d_total_io_current(o.id)["shares"], o.selling_price, plio.d_basic_results(o.id)["last"]), 
                "selling_expiration": o.selling_expiration, 
                "shares":plio.d_total_io_current(o.id)["shares"], 
                "balance_percentage": o.balance_percentage, 
                "daily_adjustment": o.daily_adjustment, 
                "selling_price": o.selling_price, 
                "is_deletable": o.is_deletable(), 
                "flag": o.products.stockmarkets.country, 
                "gains_at_selling_point_investment": o.selling_price*o.products.real_leveraged_multiplier()*plio.d_total_io_current(o.id)["shares"]-plio.d_total_io_current(o.id)["invested_investment"], 
                "decimals": o.decimals, 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)


    @action(detail=True, methods=["get"], name='Investments operations evolution chart', url_path="operations_evolution_chart", url_name='operations_evolution_chart', permission_classes=[permissions.IsAuthenticated])
    def operations_evolution_chart(self, request, pk=None):
        investment=self.get_object()
        plio=ios.IOS.from_ids(timezone.now(), request.user.profile.currency, [investment.id, ], 1)
        if len(plio.d_io(investment.id))==0:
            return JsonResponse( _("Insuficient data") , encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        
        qs_dividends=models.Dividends.objects.all().filter(investments=investment).order_by('datetime')
        #Gets investment important datetimes: operations, dividends, init and current time. For each datetime adds another at the beginning of the day, to get mountains in graph
        datetimes=set()
        datetimes.add(plio.d_io(investment.id)[0]["datetime"]-timedelta(seconds=1))
        for op in plio.d_io(investment.id):
            datetimes.add(op["datetime"])
            datetimes.add(op["datetime"]+timedelta(seconds=1))
        for dividend in qs_dividends:
            datetimes.add(dividend.datetime)
        datetimes.add(timezone.now())
        datetimes_list=list(datetimes)
        datetimes_list.sort()
        
        invested=[]
        gains_dividends=[]
        balance=[]
        dividends=[]
        gains=[]
        
        for i, dt in enumerate(datetimes_list):
            plio_dt=ios.IOS.from_ids( dt, request.user.profile.currency, [investment.id, ], 2)
            #Calculate dividends in datetime
            dividend_net=0
            for dividend in qs_dividends:
                if dividend.datetime<=dt:
                    dividend_net=dividend_net+dividend.net
    
            #Append data of that datetime
            invested.append(plio_dt.d_total_io_current(investment.id)["invested_user"])
            balance.append(plio_dt.d_total_io_current(investment.id)["balance_futures_user"])
            gains_dividends.append(plio_dt.d_total_io_historical(investment.id)["gains_net_user"]+dividend_net)
            dividends.append(dividend_net)
            gains.append(plio_dt.d_total_io_historical(investment.id)["gains_net_user"])
        d= {
            "datetimes": datetimes_list, 
            "invested": invested, 
            "balance":balance, 
            "gains_dividends":gains_dividends, 
            "dividends": dividends, 
            "gains": gains, 
        }
        return JsonResponse( d, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class InvestmentsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Investmentsoperations.objects.select_related("investments").select_related("investments__products").all()
    serializer_class = serializers.InvestmentsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.investments.set_attributes_after_investmentsoperations_crud()
        return Response(status=status.HTTP_204_NO_CONTENT)    

class AccountsViewSet(viewsets.ModelViewSet):
    queryset = models.Accounts.objects.select_related("banks").all()
    serializer_class = serializers.AccountsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def queryset_for_list_methods(self):
        active=RequestBool(self.request, 'active')
        bank_id=RequestInteger(self.request, 'bank')

        if bank_id is not None:
            self.queryset=self.queryset.filter(banks__id=bank_id,   active=True)
        elif active is not None:
            self.queryset=self.queryset.filter(active=active)

        return self.queryset
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=False, type=OpenApiTypes.BOOL), 
            OpenApiParameter(name='bank', description='Filter by bank', required=False, type=OpenApiTypes.URI), 
        ],
    )
    def list(self, request):
        serializer = serializers.AccountsSerializer(self.queryset_for_list_methods(), many=True, context={'request': request})
        return Response(serializer.data)


    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=False, type=OpenApiTypes.BOOL), 
            OpenApiParameter(name='bank', description='Filter by bank', required=False, type=OpenApiTypes.URI), 
        ],
    )
    @action(detail=False, methods=["get"], name='List accounts with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):
        r=[]
        for o in self.queryset_for_list_methods():
            balance=o.balance(timezone.now(), request.user.profile.currency ) 
            r.append({
                "id": o.id,  
                "name": o.name, 
                "active":o.active, 
                "url":request.build_absolute_uri(reverse('accounts-detail', args=(o.pk, ))), 
                "number": o.number, 
                "balance_account": balance["balance_account_currency"] ,  
                "balance_user": balance["balance_user_currency"], 
                "is_deletable": o.is_deletable(), 
                "currency": o.currency, 
                "banks":request.build_absolute_uri(reverse('banks-detail', args=(o.banks.pk, ))), 
                "localname": _(o.name), 
                "decimals": o.decimals, 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class AccountsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Accountsoperations.objects.select_related(
        "accounts",
        "concepts", 
        "associated_transfer__origin__banks", 
        "associated_transfer__destiny__banks", 
        "dividends__investments__accounts", 
        "investmentsoperations__investments", 
    ).all()
    serializer_class = serializers.AccountsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', description='Filter by search', required=False, type=OpenApiTypes.STR), 
            OpenApiParameter(name='concept', description='Filter by concept', required=False, type=OpenApiTypes.URI), 
            OpenApiParameter(name='year', description='Filter by year', required=False, type=OpenApiTypes.INT), 
            OpenApiParameter(name='month', description='Filter by month', required=False, type=OpenApiTypes.INT), 
        ],
    )
    def list(self, request):     
        search=RequestString(self.request, 'search')
        concept=RequestUrl(self.request, 'concept', models.Concepts)
        year=RequestInteger(self.request, 'year')
        month=RequestInteger(self.request, 'month')
        account=RequestUrl(self.request, 'account', models.Accounts)

        if search is not None:
            self.queryset=self.queryset.filter(comment__icontains=search)
        elif all_args_are_not_none(account, year, month):
            dt_initial=casts.dtaware_month_start(year, month, request.user.profile.zone)
            initial_balance=account.balance( dt_initial, request.user.profile.currency)['balance_account_currency']
            self.queryset=self.queryset.filter(accounts=account, datetime__year=year, datetime__month=month).order_by("datetime")
            serializer = serializers.AccountsoperationsSerializer(self.queryset, many=True, context={'request': request})
            for d in serializer.data:
                d["balance"]=initial_balance+d["amount"]
                initial_balance+=d["amount"]
            functions.show_queries_function()
            return Response(serializer.data)
        elif all_args_are_not_none(concept, year, month):
            self.queryset=self.queryset.filter(concepts=concept, datetime__year=year, datetime__month=month)
        elif all_args_are_not_none(concept, year):
            self.queryset=self.queryset.filter(concepts=concept, datetime__year=year)
        serializer = serializers.AccountsoperationsSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)


    @action(detail=True, methods=['POST'], name='Refund all cco paid in an ao', url_path="ccpaymentrefund", url_name='ccpaymentrefund', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def ccpaymentrefund(self, request, pk=None):
        ao=self.get_object()
        models.Creditcardsoperations.objects.filter(accountsoperations_id=ao.id).update(paid_datetime=None,  paid=False, accountsoperations_id=None)
        ao.delete() #Must be at the end due to middle queries
        return JsonResponse( True, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

class AccountstransfersViewSet(viewsets.ModelViewSet):
    queryset = models.Accountstransfers.objects.all()
    serializer_class = serializers.AccountstransfersSerializer
    permission_classes = [permissions.IsAuthenticated]  

class BanksViewSet(viewsets.ModelViewSet):
    queryset = models.Banks.objects.all()
    permission_classes = [permissions.IsAuthenticated]  
    serializer_class =  serializers.BanksSerializer

    def queryset_for_list_methods(self):
        active=RequestBool(self.request, "active")
        if active is not None:
            self.queryset=self.queryset.filter(active=active)
        return self.queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active banks', required=False, type=OpenApiTypes.BOOL), 
        ],
    )
    def list(self, request):
        serializer = serializers.BanksSerializer(self.queryset_for_list_methods(), many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active banks', required=False, type=OpenApiTypes.BOOL), 
        ],
    )
    @action(detail=False, methods=["get"], name='List banks with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):
        r=[]
        for o in self.queryset_for_list_methods():
            balance_accounts=o.balance_accounts()
            balance_investments=o.balance_investments(request)
            r.append({
                "id": o.id,  
                "name": o.name, 
                "active":o.active, 
                "url":request.build_absolute_uri(reverse('banks-detail', args=(o.pk, ))), 
                "balance_accounts": balance_accounts, 
                "balance_investments": balance_investments, 
                "balance_total": balance_accounts+balance_investments, 
                "is_deletable": o.is_deletable(), 
                "localname": _(o.name), 
            })
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)
        




class IOS(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        request=serializers.IOSRequestSerializer, 
        description="Makes a IOS object", 
    )
    def post(self, request, *args, **kwargs):
        """
            This view interacts with IOS module
        """
        classmethod_str=RequestString(request, "classmethod_str")
        addition_current_year_gains=RequestBool(request, "addition_current_year_gains", False)
        if classmethod_str is None:
            return Response({'status': "classmethod_str can't be null"}, status=status.HTTP_400_BAD_REQUEST)
        dt=RequestDtaware(request, "datetime", request.user.profile.zone, timezone.now())
        mode=RequestInteger(request, "mode", ios.IOSModes.ios_totals_sumtotals)
        
        #Preparing simulation
        simulation=request.data["simulation"] if request.data["simulation"] else []
        
        for s in simulation:
            if s["datetime"].__class__==str: #When comes from a post
                s["datetime"]=casts.str2dtaware(s["datetime"], "JsUtcIso")
                s["shares"]=Decimal(s["shares"])
                s["taxes"]=Decimal(s["taxes"])
                s["commission"]=Decimal(s["commission"])
                s["price"]=Decimal(s["price"])
                s["currency_conversion"]=Decimal(s["currency_conversion"])

    #    print(dt, mode, simulation)
        if classmethod_str=="from_ids":
            ids=RequestListOfIntegers(request, "investments")
            if all_args_are_not_none( ids, dt, mode, simulation):
                ios_=ios.IOS.from_ids( dt,  request.user.profile.currency,  ids,  mode, simulation)
                if addition_current_year_gains:
                    ios_.io_current_addition_current_year_gains()
                return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        elif classmethod_str=="from_all":
                ios_=ios.IOS.from_all( dt,  request.user.profile.currency,  mode, simulation)
                if addition_current_year_gains:
                    ios_.io_current_addition_current_year_gains()
                return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        elif classmethod_str=="from_all_merging_io_current":
                ios_=ios.IOS.from_qs_merging_io_current( dt,  request.user.profile.currency, models.Investments.objects.all(),   mode, simulation)
                if addition_current_year_gains:
                    ios_.io_current_addition_current_year_gains()
                return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        elif classmethod_str=="from_ids_merging_io_current":
            ids=RequestListOfIntegers(request, "investments")
            if all_args_are_not_none( ids, dt, mode, simulation):
                ios_=ios.IOS.from_qs_merging_io_current( dt,  request.user.profile.currency, models.Investments.objects.filter(id__in=ids),   mode, simulation)
                if addition_current_year_gains:
                    ios_.io_current_addition_current_year_gains()
                return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

        return Response({'status': "classmethod_str wasn't found'"}, status=status.HTTP_400_BAD_REQUEST)

@transaction.atomic
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsChangeSellingPrice(request):
    selling_price=RequestDecimal(request, "selling_price")
    selling_expiration=RequestDate(request, "selling_expiration")
    investments=RequestListOfUrls(request, "investments", models.Investments)
    ids=[]
    if investments is not None and selling_price is not None: #Pricce 
        with transaction.atomic():
            for inv in investments:
                ids.append(inv.id)
                inv.selling_price=selling_price
                inv.selling_expiration=selling_expiration
                inv.save()
        r   = serializers.InvestmentsSerializer(models.Investments.objects.filter(id__in=ids), many=True, context={'request': request}).data
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)
    return Response({'status': 'Investment or selling_price is None'}, status=status.HTTP_404_NOT_FOUND)



@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def Currencies(request):
    """
        Function REturns a list of used currencies, last change and if it's supported
        a/b=factor a=factor b. EUR/USD= 1.09 => 1 EUR =1.09 USD
    """
    supported=[
        ("EUR", "USD", 74747),
    ]
    r=[]
    for a,  b in list(permutations(models.Assets.currencies(), 2)):
        final_product_id=None
        final_inverted=True
        can_c=False
        is_supported=False
        for (sa, sb, products_id) in supported:
            if a==sa and b==sb:
                can_c = True
                final_product_id=products_id
                final_inverted=False
                is_supported=True
                break
            if a==sb and b==sa:
                can_c = False
                final_product_id=products_id
                final_inverted=True
                is_supported=True
                break
        price=None
        datetime_=None
        quote_url=None
        product_url=None
        if final_product_id is not None:
            qs=models.Quotes.objects.filter(datetime__lte=timezone.now(), products__id=products_id).order_by("-datetime")
            quote= qs[0] if qs.exists() else None
            if quote is not None:
                datetime_=quote.datetime
                if final_inverted is False:
                    price=quote.quote
                    quote_url=models.Quotes.hurl(request, quote.id)
                    product_url=models.Products.hurl(request, quote.products.id)
                else:
                    price=1/quote.quote
        
        r.append({
            "from": a, 
            "to": b, 
            "can_c": can_c, 
            "can_rud": True if quote_url else False, 
            "datetime": datetime_, 
            "quote": price, 
            "quote_url": quote_url, 
            "supported": is_supported, 
            "product_url": product_url, 
        })
    
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class LeveragesViewSet(CatalogModelViewSet):
    queryset = models.Leverages.objects.all()
    serializer_class = serializers.LeveragesSerializer

@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def MaintenanceCatalogsUpdate(request):
    internet=RequestBool(request, "internet", False)
    if internet is True: #Github code update
        call_command("loaddata_catalogs", "--internet")
    else: # Current Code update
        call_command("loaddata_catalogs")
    return Response({'status': 'Catalogs updated'}, status=status.HTTP_200_OK)
    
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsPairs(request):
    """
        @param currency_conversion Boolean. If product's hasn't currency conversion this can help
    """
    product_better=RequestUrl(request, "a", models.Products)
    product_worse=RequestUrl(request, "b", models.Products)
    interval_minutes=RequestInteger(request, "interval_minutes", 1)

    with connection.cursor() as c:
        c.execute("""
            select 
                a.datetime, 
                a.datetime-b.datetime as diff, 
                a.quote as quote_a, 
                b.quote as quote_b, 
                a.products_id as product_a, 
                b.products_id as product_b  
            from 
                (select * from quotes where products_id=%s) as a, 
                (select * from quotes where products_id=%s) as b 
            where 
                date_trunc('hour',a.datetime)=date_trunc('hour',b.datetime) and 
                a.datetime-b.datetime between %s and %s     
            order by
                a.datetime
        """, [product_worse.id, product_better.id, timedelta(minutes=-interval_minutes), timedelta(minutes=interval_minutes) ])
        common_quotes=functions.dictfetchall(c)
    
    
    r={}
    r["product_a"]={"name":product_better.fullName(), "currency": product_better.currency, "url": request.build_absolute_uri(reverse('products-detail', args=(product_better.id, ))), "current_price": product_better.basic_results()["last"]}
    r["product_b"]={"name":product_worse.fullName(), "currency": product_worse.currency, "url": request.build_absolute_uri(reverse('products-detail', args=(product_worse.id, ))), "current_price": product_worse.basic_results()["last"]}
    r["data"]=[]
    if len(common_quotes)>0:
        first_pr=common_quotes[0]["quote_b"]/common_quotes[0]["quote_a"]
        for row in common_quotes:#a worse, b better
            pr=row["quote_b"]/row["quote_a"]
            r["data"].append({
                "datetime": row["datetime"], 
                "diff": int(row["diff"].total_seconds()), 
                "price_worse": row["quote_a"], 
                "price_better": row["quote_b"], 
                "price_ratio": pr, 
                "price_ratio_percentage_from_start": percentage_between(first_pr, pr), 
            })
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', 'DELETE' ])    
@permission_classes([permissions.IsAuthenticated, ])
## GET METHODS
## products/quotes/ohcl/?product_url To get all ohcls of a product
## products/quotes/ohcl/?product_url&year=2022&month=4 To get ochls of a product, in a month
## DELETE METHODS
## products/quotes/ohcl?product=url&date=2022-4-1
def ProductsQuotesOHCL(request):
    if request.method=="GET":
        product=RequestUrl(request, "product", models.Products)
        year=RequestInteger(request, "year")
        month=RequestInteger(request, "month")
        
        if product is not None and year is not None and month is not None:
            ld_ohcl=product.ohclDailyBeforeSplits()       
            product.ohclMonthlyBeforeSplits()
            r=[] ## TODO. Add from_date in postgres function to avoid this
            for d in ld_ohcl:
                if d["date"].year==year and d["date"].month==month:
                    r.append(d)
            return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

        if product is not None:
            ld_ohcl=product.ohclDailyBeforeSplits()         
            return JsonResponse( ld_ohcl, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
            
    elif request.method=="DELETE":
        product=RequestUrl(request, "product", models.Products)
        date=RequestDate(request, "date")
        if product is not None and date is not None:
            qs=models.Quotes.objects.filter(products=product, datetime__date=date)
            qs.delete()
            return JsonResponse(True, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsRanges(request):
    product=RequestUrl(request, "product", models.Products)
    totalized_operations=RequestBool(request, "totalized_operations") 
    percentage_between_ranges=RequestDecimal(request, "percentage_between_ranges")

    if percentage_between_ranges is not None:
        percentage_between_ranges=percentage_between_ranges
    percentage_gains=RequestDecimal(request, "percentage_gains")
    if percentage_gains is not None:
        percentage_gains=percentage_gains
    amount_to_invest=RequestDecimal(request, "amount_to_invest")
    recomendation_methods=RequestInteger(request, "recomendation_methods")
    investments=RequestListOfUrls(request,"investments[]", models.Investments) 
    if investments is None:
        qs_investments=models.Investments.objects.none()
    else:
        if all_args_are_not_none(*investments):
            qs_investments=models.Investments.objects.filter(id__in=[investment.id for investment in investments])
        else: 
            qs_investments=models.Investments.objects.none()
    additional_ranges=RequestInteger(request, "additional_ranges", 3)

    if not models.Quotes.objects.filter(products=product).exists():    
        return Response(_("This product hasn't quotes. You need at least one"),  status=status.HTTP_400_BAD_REQUEST)

    if all_args_are_not_none(product, totalized_operations,  percentage_between_ranges, percentage_gains, amount_to_invest, recomendation_methods):
        from moneymoney.productrange import ProductRangeManager
        
        prm=ProductRangeManager(request, product, percentage_between_ranges, percentage_gains, totalized_operations,  qs_investments=qs_investments, decimals=product.decimals, additional_ranges=additional_ranges)
        prm.setInvestRecomendation(recomendation_methods)

        return JsonResponse( prm.json(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
    return Response( status=status.HTTP_400_BAD_REQUEST)
    
    
## Has annotate investments__count en el queryset
## Solo afectaría a personal products<0. Solo investments, ya que todas las demás dependen de produto y habría que borrarllas
## Es decir si borro un producto, borraría quotes, splits, estimatiosn.....
class ProductsViewSet(viewsets.ModelViewSet):
    queryset = models.Products.objects.select_related("productstypes","leverages", "stockmarkets").all().annotate(uses=Count('investments', distinct=True))
    serializer_class = serializers.ProductsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if  instance.id<10000000:#System product
            if  not request.user.groups.filter(name="CatalogManager").exists():
                raise ValidationError(_("You can't delete a system product if you're not a Catalog Manager (only developers)"))    
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], name='Delete last quote of the product', url_path="delete_last_quote", url_name='delete_last_quote', permission_classes=[permissions.IsAuthenticated])
    def delete_last_quote(self, request, pk=None):
        product = self.get_object()
        instance = models.Quotes.objects.filter(products=product).order_by("-datetime")[0]
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
        

    @action(detail=False, methods=["GET"], url_path='search_with_quotes', url_name='search_with_quotes')
    def search_with_quotes(self, request, *args, **kwargs):
        """
            Search products and return them with last, penultimate, and last year quotes
        """
  
        search=RequestString(request, "search")
        if all_args_are_not_none(search):
            
            if search ==":FAVORITES":
                ids=list(request.user.profile.favorites.all().values_list("id",  flat=True).distinct())
            elif search==":INVESTMENTS":
                ids=list(models.Investments.objects.all().values_list("products__id",  flat=True).distinct())
            elif search==":ACTIVE_INVESTMENTS":
                ids=list(models.Investments.objects.filter(active=True).values_list("products__id",  flat=True).distinct())
            elif search==":PERSONAL":
                ids=list(models.Products.objects.filter(id__gt=10000000).values_list('id', flat=True))
            elif search==":INDICES":
                ids=list(models.Products.objects.filter(productstypes=models.Productstypes.objects.get(pk=eProductType.Index)).values_list('id', flat=True))
            elif search==":CFD_FUTURES":
                ids=list(models.Products.objects.filter(productstypes__in=(models.Productstypes.objects.get(pk=eProductType.CFD), models.Productstypes.objects.get(pk=eProductType.Future))).values_list('id', flat=True))
            elif search==":ETF":
                ids=list(models.Products.objects.filter(productstypes=models.Productstypes.objects.get(pk=eProductType.ETF)).values_list('id', flat=True))
            elif search==":BONDS":
                ids=list(models.Products.objects.filter(productstypes__in=(models.Productstypes.objects.get(pk=eProductType.PublicBond), models.Productstypes.objects.get(pk=eProductType.PrivateBond))).values_list('id', flat=True))
            elif search==":CURRENCIES":
                ids=list(models.Products.objects.filter(productstypes=models.Productstypes.objects.get(pk=eProductType.Currency)).values_list('id', flat=True))
 
            else: #use search text
                ids=list(models.Products.objects.filter(
                    Q(name__icontains=search) |
                    Q(isin__icontains=search) |
                    Q(ticker_yahoo__icontains=search) |
                    Q(ticker_investingcom__icontains=search) |
                    Q(ticker_morningstar__icontains=search) |
                    Q(ticker_google__icontains=search) |
                    Q(ticker_quefondos__icontains=search)
                ).values_list('id', flat=True))
            products=models.Products.objects.filter(id__in=ids)
            rows=[]
            for p in products:
                row={}
                row['id']=p.id
                row["product"]=p.hurl(request, p.id)
                row["last_datetime"]=None if p.basic_results()["last"] is None else p.basic_results()["last_datetime"]
                row["last"]=None if  p.basic_results()["last"] is None else p.basic_results()["last"]
                row["penultimate_datetime"]=None if  p.basic_results()["penultimate"]  is None else p.basic_results()["penultimate_datetime"]
                row["penultimate"]=None if  p.basic_results()["penultimate"] is None else p.basic_results()["penultimate"]
                row["lastyear_datetime"]=None if  p.basic_results()["lastyear"]  is None else p.basic_results()["lastyear_datetime"]
                row["lastyear"]=None if  p.basic_results()["lastyear"]  is None else p.basic_results()["lastyear"]
                row["percentage_last_year"]=None if row["lastyear"] is None else Percentage(row["last"]-row["lastyear"], row["lastyear"])
                rows.append(row)
            return JsonResponse( rows,  encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        return Response("Products search error", status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['GET'], name='Get product historical information report', url_path="historical_information", url_name='historical_information', permission_classes=[permissions.IsAuthenticated])
    def historical_information(self, request, pk=None):
        product=self.get_object()
 
        # Query with las datetime grouped by year, month
        qs_last_datetimes_by_ym=models.Quotes.objects.filter(products=product)\
            .values("datetime__year","datetime__month").annotate(last=Max("datetime"))
        # Query to get quotes with that datetimes
        qs_quotes_last_ym=models.Quotes.objects.filter(products=product, datetime__in=Subquery(qs_last_datetimes_by_ym.values("last"))).order_by("datetime")
        lod_newquotes=list(qs_quotes_last_ym.values("datetime__year", "datetime__month", "quote"))
        
        # Transposition lod
        lod_transposition=lod_ymv.lod_ymv_transposition(lod_newquotes, "datetime__year", "datetime__month", "quote")
        lod_percentage=lod_ymv.lod_ymv_transposition_with_percentages(lod_transposition)
        
        r={"quotes":lod_transposition, "percentages":lod_percentage}
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

class ProductspairsViewSet(viewsets.ModelViewSet):
    queryset = models.Productspairs.objects.all()
    serializer_class = serializers.ProductspairsSerializer
    permission_classes = [permissions.IsAuthenticated]  

class ProductstypesViewSet(CatalogModelViewSet):
    queryset = models.Productstypes.objects.all()
    serializer_class = serializers.ProductstypesSerializer

@api_view(['POST', ])
@permission_classes([permissions.IsAuthenticated, ])
def ProductsUpdate(request):
    from moneymoney.investing_com import InvestingCom
    auto=RequestBool(request, "auto", False) ## Uses automatic request with settings globals investing.com   
    if auto is True:
        with TemporaryDirectory() as tmp:
            run(f"""wget --header="Host: es.investing.com" \
                --header="User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0" \
                --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
                --header="Accept-Language: es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3" \
                --header="Accept-Encoding: gzip, deflate, br" \
                --header="Alt-Used: es.investing.com" \
                --header="Connection: keep-alive" \
                --referer="{request.user.profile.investing_com_referer}" \
                --header="{request.user.profile.investing_com_cookie}" \
                --header="Upgrade-Insecure-Requests: 1" \
                --header="Sec-Fetch-Dest: document" \
                --header="Sec-Fetch-Mode: navigate" \
                --header="Sec-Fetch-Site: same-origin" \
                --header="Sec-Fetch-User: ?1" \
                --header="Pragma: no-cache" \
                --header="Cache-Control: no-cache" \
                --header="TE: trailers" \
                "{request.user.profile.investing_com_url}" -O {tmp}/portfolio.csv""", shell=True, capture_output=True)
            ic=InvestingCom.from_filename_in_disk(request.user.profile.zone, f"{tmp}/portfolio.csv")
    else:
        # if not GET, then proceed
        if "csv_file1" not in request.FILES:
            return Response({'status': 'You must upload a file'}, status=status.HTTP_404_NOT_FOUND)
        else:
            csv_file = request.FILES["csv_file1"]
            
        if not csv_file.name.endswith('.csv'):
            return Response({'status': 'File is not CSV type'}, status=status.HTTP_404_NOT_FOUND)

        #if file is too large, return
        if csv_file.multiple_chunks():
            return Response({'status': "Uploaded file is too big ({} MB).".format(csv_file.size/(1000*1000),)}, status=status.HTTP_404_NOT_FOUND)

        ic=InvestingCom.from_filename_in_memory(request.user.profile.zone, csv_file)
    r=ic.get()
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)
    
class Profile(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        p=models.Profile.objects.filter(user=request.user)[0]
        favorites=[]
        for product in p.favorites.all():
            favorites.append(request.build_absolute_uri(reverse('products-detail', args=(product.id, ))))
        r={
            "currency": p.currency, 
            "email": p.user.email, 
            "favorites": favorites, 
            "first_name":p.user.first_name, 
            "last_name": p.user.last_name, 
            "invest_amount_1": p.invest_amount_1, 
            "invest_amount_2": p.invest_amount_2, 
            "invest_amount_3": p.invest_amount_3, 
            "invest_amount_4": p.invest_amount_4, 
            "invest_amount_5": p.invest_amount_5, 
            "investing_com_url": p.investing_com_url, 
            "investing_com_cookie": p.investing_com_cookie, 
            "investing_com_referer": p.investing_com_referer, 
            "zone": p.zone, 
            "annual_gains_target": p.annual_gains_target, 
        }
        return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
        
    @transaction.atomic
    def put(self, request):
        p=models.Profile.objects.get(user=request.user)
        
        if "newp" in request.data and request.data["newp"]!="":
            p.user.set_password(request.data["newp"])
            print("PASSWORD SET")
    
        if "toggle_favorite" in request.data:
            toggle_favorite=RequestUrl(request, "toggle_favorite", models.Products)
            if p.favorites.contains(toggle_favorite):
                p.favorites.remove(toggle_favorite)
            else:
                p.favorites.add(toggle_favorite)
        
        p.currency=request.data["currency"]
        p.user.email=request.data["email"]
        p.user.first_name=request.data["first_name"]
        p.user.last_name=request.data["last_name"]
        p.invest_amount_1=request.data["invest_amount_1"]
        p.invest_amount_2=request.data["invest_amount_2"]
        p.invest_amount_3=request.data["invest_amount_3"]
        p.invest_amount_4=request.data["invest_amount_4"]
        p.invest_amount_5=request.data["invest_amount_5"]
        p.investing_com_url=request.data["investing_com_url"]
        p.investing_com_cookie=request.data["investing_com_cookie"]
        p.investing_com_referer=request.data["investing_com_referer"]
        p.zone=request.data["zone"]
        p.annual_gains_target=request.data["annual_gains_target"]

        p.user.save()
        p.save()
        return self.get(request)

class QuotesMassiveUpdate(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        description="Post quotes massively", 
        request=None, 
        responses=OpenApiTypes.OBJECT
    )
    ## type==1 models.Investments historical file
    def post(self, request, *args, **kwargs):
        from moneymoney.investing_com import InvestingCom
        product=RequestUrl(request, "product", models.Products)
        bytes_=b64decode(request.data["doc"])

        ic=InvestingCom(request, product)
        ic.load_from_bytes(bytes_)
        r=ic.append_from_historical_rare_date()        
        return JsonResponse( r,  encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)
 
class QuotesViewSet(viewsets.ModelViewSet):
    queryset = models.Quotes.objects.all().select_related("products")
    serializer_class = serializers.QuotesSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    @extend_schema(
        description="""
api/quotes/ Show all quotes of the database
api/quotes/?future=true Show all quotes with datetime in the future for debugging
api/quotes/?last=true Shows all products last Quotes
api/quotes/?product=url Showss all quotes of a product
api/quotes/?product=url&month=1&year=2021 Showss all quotes of a product in a month
        """, 
        parameters=[
            OpenApiParameter(name='product', description='Filter by product', required=False, type=OpenApiTypes.URI), 
            OpenApiParameter(name='future', description='Filter by quotes set in future', required=False, type=OpenApiTypes.BOOL), 
            OpenApiParameter(name='last', description='Filter by last quotes', required=False, type=OpenApiTypes.BOOL), 
            OpenApiParameter(name='month', description='Filter by month', required=False, type=OpenApiTypes.INT), 
            OpenApiParameter(name='year', description='Filter by year', required=False, type=OpenApiTypes.INT), 
        ],
    )
    def list(self, request):
        product=RequestUrl(self.request, 'product', models.Products)
        future=RequestBool(self.request, 'future')
        last=RequestBool(self.request, 'last')
        month=RequestInteger(self.request, 'month')
        year=RequestInteger(self.request, 'year')
        
        if future is True:
            self.queryset=self.queryset.filter(datetime__gte=timezone.now()).select_related("products").order_by("datetime")
        elif last is True:## Search last quote of all products with quotes
            self.queryset=models.Quotes.qs_last_quotes().select_related("products")
        elif all_args_are_not_none(product, year, month):
            self.queryset=self.queryset.filter(products=product, datetime__year=year, datetime__month=month).order_by("datetime")
        elif product is not None:
            self.queryset=self.queryset.filter(products=product).order_by("datetime")
        serializer = serializers.QuotesSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def RecomendationMethods(request): 
    r=[]
    for id, name in models.RANGE_RECOMENDATION_CHOICES:
        r.append({
            "id":id, 
            "name":name, 
            "localname": _(name), 
        })
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualRevaluation(request ):
    only_zero=RequestBool(request, "only_zero", False)
    ld=[]
    investments=models.Investments.objects.filter(active=True).select_related("accounts","products")
    if only_zero is True:
        investments=investments.filter(products__percentage=0)
    ios_=ios.IOS.from_qs( timezone.now(), request.user.profile.currency, investments, 1)
    ios_.io_current_addition_current_year_gains()
    for inv in ios_.qs_investments():
        for o in ios_.d_io_current(inv.id):
            o["name"]=inv.fullName()
            if o["datetime"]<=casts.dtaware_year_end(date.today().year-1, request.user.profile.zone):
                o["balance_last_year_or_invested"]=o["shares"]*ios_.d_basic_results(inv.id)["lastyear"]*o["investment2account"]*o["account2user"]
            else:
                o["balance_last_year_or_invested"]=o["invested_user"]
            ld.append(o)
    ld=lod.lod_order_by(ld, "datetime")
    
    return JsonResponse( ld, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportAnnual(request, year):
    def month_results(month, month_name, local_currency):
        return month, month_name, models.Assets.pl_total_balance(casts.dtaware_month_end(year, month, request.user.profile.zone), local_currency)
    #####################
    
    dtaware_last_year=casts.dtaware_year_end(year-1, request.user.profile.zone)
    last_year=models.Assets.pl_total_balance(dtaware_last_year, request.user.profile.currency)
    list_=[]
    futures=[]
    
    # HA MEJORADO UNOS 5 segundos de 7 a 2
    for month_name, month in (
        (_("January"), 1), 
        (_("February"), 2), 
        (_("March"), 3), 
        (_("April"), 4), 
        (_("May"), 5), 
        (_("June"), 6), 
        (_("July"), 7), 
        (_("August"), 8), 
        (_("September"), 9), 
        (_("October"), 10), 
        (_("November"), 11), 
        (_("December"), 12), 
    ):
        if year==date.today().year and month>date.today().month:
            continue
        future= month_results(month,  month_name, request.user.profile.currency)
        futures.append(future)
        
    last_month=last_year['total_user']
    for future in futures:
        month, month_name,  total = future
        list_.append({
            "month_number":month, 
            "month": month_name,
            "account_balance":total['accounts_user'], 
            "investment_balance":total['investments_user'], 
            "total":total['total_user'] , 
            "percentage_year": percentage_between(last_year['total_user'], total['total_user'] ), 
            "diff_lastmonth": total['total_user']-last_month, 
        })
        last_month=total['total_user']
        
    r={"last_year_balance": last_year['total_user'],  "dtaware_last_year": dtaware_last_year,  "data": list_}
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncome(request, year):
    list_=[]
    dt_year_from=casts.dtaware_year_start(year, request.user.profile.zone)
    dt_year_to=casts.dtaware_year_end(year, request.user.profile.zone)
    
    plio=ios.IOS.from_all( dt_year_to, request.user.profile.currency, 1)
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request, dt_from=dt_year_from, dt_to=dt_year_to), "year")
    d_incomes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Income, year=year, exclude_dividends=True), "year")
    d_expenses=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Expense, year=year, exclude_dividends=True), "year")
    d_fast_operations=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.FastOperations, year=year, exclude_dividends=True), "year")

    for month_name, month in (
        (_("January"), 1), 
        (_("February"), 2), 
        (_("March"), 3), 
        (_("April"), 4), 
        (_("May"), 5), 
        (_("June"), 6), 
        (_("July"), 7), 
        (_("August"), 8), 
        (_("September"), 9), 
        (_("October"), 10), 
        (_("November"), 11), 
        (_("December"), 12), 
    ):
        if year==date.today().year and month>date.today().month:
            continue
        dividends= d_dividends[year][f"m{month}"]  if year in d_dividends else 0
        incomes=d_incomes[year][f"m{month}"] if year in d_incomes else 0
        expenses=d_expenses[year][f"m{month}"] if year in d_expenses else 0
        fast_operations=d_fast_operations[year][f"m{month}"] if year in d_fast_operations else 0
        dt_from=casts.dtaware_month_start(year, month,  request.user.profile.zone)
        dt_to=casts.dtaware_month_end(year, month,  request.user.profile.zone)
        gains=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user")
        list_.append({
            "id": f"{year}/{month}/", 
            "month_number":month, 
            "month": month_name,
            "incomes":incomes, 
            "expenses":expenses, 
            "gains":gains,  
            "fast_operations": fast_operations, 
            "dividends":dividends, 
            "total":incomes+gains+expenses+dividends+fast_operations,  
        })
    
    return JsonResponse( list_, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncomeDetails(request, year, month):
    def listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, operationstypes_id, local_currency, local_zone):
        r=[]
        i=0
        for currency in models.Accounts.currencies(): #Iterate over currencies
            qs_ao=models.Accountsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, datetime__year=year, datetime__month=month,  accounts__currency=currency).values(
                "datetime", 
                "concepts", 
                "amount", 
                "comment", 
                "accounts", 
            )
            # Excludes dividends from Accountsoperations to avoid count the in incomes and in dividend
            qs_ao=qs_ao.exclude(concepts__id__in=eConcept.dividends())
            
            for o in qs_ao:
                i-=1
                r.append({
                    "id":i, 
                    "datetime": o["datetime"], 
                    "concepts": models.Concepts.hurl(request, o["concepts"]), 
                    "amount":o["amount"]* models.Quotes.get_currency_factor(o["datetime"], currency, local_currency , None), 
                    "nice_comment":f"[AO] {o['comment']}", 
                    "currency": currency, 
                    "accounts": models.Accounts.hurl(request, o["accounts"]), 
                })
            
            qs_cco=models.Creditcardsoperations.objects.filter(concepts__operationstypes__id=operationstypes_id, datetime__year=year, datetime__month=month,  creditcards__accounts__currency=currency).values(
                "datetime", 
                "concepts", 
                "amount", 
                "comment", 
                "creditcards__accounts", 
            )
            
            for o in qs_cco:
                i-=1
                r.append({
                    "id":i, 
                    "datetime": o["datetime"], 
                    "concepts": models.Concepts.hurl(request, o["concepts"]), 
                    "amount":o["amount"]* models.Quotes.get_currency_factor(o["datetime"], currency, local_currency, None ), 
                    "nice_comment":f"[CCO] {o['comment']}", 
                    "currency": currency, 
                    "accounts": models.Accounts.hurl(request, o["creditcards__accounts"]), 
                })
                
        return lod.lod_order_by(r, "datetime")        
        
    def dividends():
        #TODO: Should use all currencies
        qs=models.Dividends.objects.filter(datetime__year=year, datetime__month=month).order_by('datetime').select_related("investments").select_related("investments__accounts")
        return serializers.DividendsSerializer(qs, many=True, context={'request': request}).data
    def listdict_investmentsoperationshistorical(request, year, month, local_currency, local_zone):
        list_ioh=[]
        dt_year_month=casts.dtaware_month_end(year, month, local_zone)
        ioh_id=0#To avoid vue.js warnings
        
        plio=ios.IOS.from_all( dt_year_month, request.user.profile.currency, 1)
        for investment in plio.qs_investments():
            for ioh in plio.d_io_historical(investment.id):
                if ioh["dt_end"].year==year and ioh["dt_end"].month==month:
                    ioh["id"]=ioh_id
                    ioh["name"]=investment.fullName()
                    ioh["operationstypes"]=request.build_absolute_uri(reverse('operationstypes-detail', args=(ioh["operationstypes_id"],  )))
                    ioh["currency_user"]=request.user.profile.currency
                    list_ioh.append(ioh)
                    ioh_id=ioh_id+1
        list_ioh= sorted(list_ioh,  key=lambda item: item['dt_end'])
        return list_ioh
    ####
    r={}
    r["expenses"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.Expense,  request.user.profile.currency, request.user.profile.zone, )
    r["incomes"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.Income,  request.user.profile.currency, request.user.profile.zone)
    r["dividends"]=dividends()
    r["fast_operations"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.FastOperations,  request.user.profile.currency, request.user.profile.zone)
    r["gains"]=listdict_investmentsoperationshistorical(request, year, month, request.user.profile.currency, request.user.profile.zone)
    
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualGainsByProductstypes(request, year):
    dt_from=casts.dtaware_year_start(year, request.user.profile.zone)
    dt_to=casts.dtaware_year_end(year, request.user.profile.zone)

    
    # Initializate dict_dividends_by_producttype
    dict_dividends_by_producttype={}
    productstypes=models.Productstypes.objects.all()
    for pt in productstypes:
        dict_dividends_by_producttype[pt.id]={"net":0, "gross":0}
    
    # Load dividends net and gross
    for dividend in models.Dividends.objects.filter(datetime__year=year).select_related("investments__products__productstypes"):
        dict_dividends_by_producttype[dividend.investments.products.productstypes.id]["gross"]+=dividend.gross
        dict_dividends_by_producttype[dividend.investments.products.productstypes.id]["net"]+=dividend.net

    plio=ios.IOS.from_all( dt_to, request.user.profile.currency, ios.IOSModes.ios_totals_sumtotals)
    l=[]
    for pt in productstypes:
        gains_net=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user", pt.id)
        gains_gross=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_gross_user", pt.id)
        l.append({
                "id": pt.id, 
                "name":_(pt.name), 
                "gains_gross": gains_gross, 
                "dividends_gross": dict_dividends_by_producttype[pt.id]["gross"], 
                "gains_net":gains_net, 
                "dividends_net": dict_dividends_by_producttype[pt.id]["net"], 
        })      
        
    d_fast_operations=models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.FastOperations, year=year)

    l.append({
            "id": -1000, #Fast operations
            "name":_("Fast operations"), 
            "gains_gross": d_fast_operations[0]["total"] if len(d_fast_operations)>0 else 0,
            "dividends_gross":0, 
            "gains_net": d_fast_operations[0]["total"] if len(d_fast_operations)>0 else 0, 
            "dividends_net": 0, 
    })
    return JsonResponse( l, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportConcepts(request):

    ## Get all Medians
    
    def get_median(lod):
        list_=[]
        for d in lod:
            list_.append(d["amount"])
        list_.sort()
        return median(list_)
    data={}
    for model in [models.Accountsoperations, models.Creditcardsoperations]:#Repite codigo para cada modelo
        
        qs_ao=model.objects.annotate(
            year=ExtractYear('datetime'),
            month=ExtractMonth('datetime'),
        ).values('year', 'month', 'concepts__id').annotate(sum=Sum('amount')).order_by("year", "month", "concepts_id")
        #Genera diccionario key as concept_id y dentro un lod_ymv
        for d in qs_ao:
            new_d={'year': d["year"], 'month':d["month"], "amount":d["sum"]}
            if d["concepts__id"] in data:
                data[d["concepts__id"]].append(new_d)
            else:
                data[d["concepts__id"]]=[new_d, ]

    #Makes report
    year=RequestInteger(request, "year")
    month=RequestInteger(request,  "month")
    if year is None or month is None:
        return Response({'details': _('You must set year and month parameters')}, status=status.HTTP_400_BAD_REQUEST)
        
    r={}
    r["positive"]=[]
    r["negative"]=[]
    
    month_ao_sum=list(models.Accountsoperations.objects.filter(datetime__month=month,datetime__year=year, concepts__operationstypes__id__in=[eOperationType.Income, eOperationType.Expense]).select_related("operationstypes").values("concepts__id").order_by("concepts_id").annotate(sum=Sum('amount')))+\
        list(models.Creditcardsoperations.objects.filter(datetime__month=month,datetime__year=year, concepts__operationstypes__id__in=[eOperationType.Income, eOperationType.Expense]).select_related("operationstypes").values("concepts__id").order_by("concepts_id").annotate(sum=Sum('amount')))
    total_month_positives=lod.lod_sum_positives(month_ao_sum, "sum")
    total_month_negatives=lod.lod_sum_negatives(month_ao_sum, "sum")
    dict_concepts=models.Concepts.dictionary()
    ## list
    for d in month_ao_sum:
        concept=dict_concepts[d["concepts__id"]]
        if d["sum"]>0:
            r["positive"].append({
                "concept": models.Concepts.hurl(request, d["concepts__id"]), 
                "name": concept.name, 
                "total": d["sum"], 
                "percentage_total": Percentage(d["sum"], total_month_positives), 
                "median":get_median(data[d["concepts__id"]]),
            })   
        else:
            r["negative"].append({
                "concept": models.Concepts.hurl(request, d["concepts__id"]), 
                "name": concept.name, 
                "total": d["sum"], 
                "percentage_total": Percentage(d["sum"], total_month_negatives), 
                "median":get_median(data[d["concepts__id"]]),
            })
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportDividends(request):
    qs_investments=models.Investments.objects.filter(active=True).select_related("products").select_related("accounts").select_related("products__leverages").select_related("products__productstypes")
    ld_report=[]
    for inv in qs_investments:
        shares=inv.shares_from_db_investmentsoperations()
        try:
            estimation=models.EstimationsDps.objects.get(products_id=inv.products.id, year=timezone.now().year)
        except: 
            estimation=None
            
        if estimation is None:
            estimation=None
            date_estimation=None
            dps=None
            percentage=Percentage()
            estimated=None
        else:
            dps=estimation.estimation
            date_estimation=estimation.date_estimation
            percentage=Percentage(dps, inv.products.basic_results()["last"])
            estimated=shares*dps*inv.products.real_leveraged_multiplier()
            
        
        d={
            "product": inv.products.hurl(request, inv.products.id), 
            "name":  inv.fullName(), 
            "current_price": inv.products.basic_results()["last"], 
            "dps": dps, 
            "shares": shares, 
            "date_estimation": date_estimation, 
            "estimated": estimated, 
            "percentage": percentage, 
            "currency": inv.products.currency, 
        }
        ld_report.append(d)
    return JsonResponse( ld_report, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)



@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportEvolutionAssets(request, from_year):
    tb={}
    for year in range(from_year-1, date.today().year+1):
        tb[year]=models.Assets.pl_total_balance(casts.dtaware_month_end(year, 12, request.user.profile.zone), request.user.profile.currency)
        
    d_incomes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Income, exclude_dividends=True), "year")
    d_expenses=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Expense, exclude_dividends=True), "year")
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request), "year")
    d_fast_operations=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.FastOperations, exclude_dividends=True), "year")

    # Dictionary can have missing years if there isn't data in database, so I must fill them
    for year in range(from_year, date.today().year+1):
        for dict_ in [d_incomes, d_expenses, d_dividends, d_fast_operations]:
            if not year in dict_:
                dict_[year]={"total":0}

    list_=[]
    for year in range(from_year, date.today().year+1): 
        dt_from=casts.dtaware_year_start(year, request.user.profile.zone)
        dt_to=casts.dtaware_year_end(year, request.user.profile.zone)
        plio=ios.IOS.from_all( dt_to, request.user.profile.currency, 1)
        dividends=d_dividends[year]["total"]
        incomes=d_incomes[year]["total"]-dividends
        expenses=d_expenses[year]["total"]
        fast_operations=d_fast_operations[year]["total"]
        gains=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user")
        list_.append({
            "year": year, 
            "balance_start": tb[year-1]["total_user"], 
            "balance_end": tb[year]["total_user"],  
            "diff": tb[year]["total_user"]-tb[year-1]["total_user"], 
            "incomes":incomes, 
            "gains_net": gains+fast_operations, 
            "dividends_net":dividends, 
            "expenses":expenses, 
            "total":incomes+gains+dividends+expenses, 
        })
    return JsonResponse( list_, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)
    
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportEvolutionAssetsChart(request):
    def month_results(year, month,  local_currency, local_zone):
        dt=casts.dtaware_month_end(year, month, local_zone)
        return dt, models.Assets.pl_total_balance(dt, local_currency, ios.IOSModes.totals_sumtotals)
    #####################
    year_from=RequestInteger(request, "from")
    if year_from==date.today().year:
        months_12=date.today()-timedelta(days=365)
        list_months=casts.months(months_12.year, months_12.month)
    else:
        list_months=casts.months(year_from, 1)
        
    l=[]
    futures=[]
    
    # HA MEJORADO UNOS 5 segundos de 10 segundos a 3 para 12 meses
    with ThreadPoolExecutor(max_workers=settings.CONCURRENCY_DB_CONNECTIONS_BY_USER) as executor:
        for year,  month in list_months:    
            futures.append(executor.submit(month_results, year, month, request.user.profile.currency,  request.user.profile.zone))

    for future in futures:
        dt, total=future.result()
        l.append({
            "datetime":dt, 
            "total_user": total["total_user"], 
            "invested_user":total["investments_invested_user"], 
            "investments_user":total["investments_user"], 
            "accounts_user":total["accounts_user"], 
            "zerorisk_user": total["zerorisk_user"], 
        })
    return JsonResponse( l, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)
    


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionInvested(request, from_year):
    list_=[]
    qs=models.Investments.objects.all().select_related("products")
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request), "year")
    d_custody_commissions=lod.lod2dod(models.Assets.lod_ym_balance_user_by_concepts(request, [eConcept.CommissionCustody, ] ), "year")
    d_fast_operations=lod.lod2dod(models.Assets.lod_ym_balance_user_by_concepts(request, [eConcept.FastInvestmentOperations, ] ), "year")
    d_taxes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_concepts(request, [eConcept.TaxesReturn, eConcept.TaxesPayment, ] ), "year")

    # Dictionary can have missing years if there isn't data in database, so I must fill them
    for year in range(from_year, date.today().year+1):
        for dict_ in [d_dividends, d_custody_commissions, d_taxes, d_fast_operations]:
            if not year in dict_:
                dict_[year]={"total":0}

    for year in range(from_year, date.today().year+1): 
        dt_from=casts.dtaware_year_start(year, request.user.profile.zone)
        dt_to=casts.dtaware_year_end(year, request.user.profile.zone)
        plio=ios.IOS.from_qs( dt_to, request.user.profile.currency, qs, 1)

        d={}
        d['year']=year
        d['invested']=plio.sum_total_io_current()["invested_user"]
        d['balance']=plio.sum_total_io_current()["balance_futures_user"]
        d['diff']=d['balance']-d['invested']
        d['percentage']=percentage_between(d['invested'], d['balance'])
        d['net_gains_plus_dividends_plus_fo']=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user")+d_dividends[year]["total"] + d_fast_operations[year]["total"]
        d['custody_commissions']=d_custody_commissions[year]["total"]
        d['taxes']=d_taxes[year]["total"] 
        d['investment_commissions']=plio.io_sum_between_dt(dt_from, dt_to, "commission_account")
        list_.append(d)
    
    return JsonResponse( list_, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)







@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportsInvestmentsLastOperation(request):
    method=RequestInteger(request, "method", 0)
    investments=models.Investments.objects.filter(active=True).select_related("accounts", "products", "products__stockmarkets")
    if method==0: #Separated investments
        ios_=ios.IOS.from_qs( timezone.now(), request.user.profile.currency, investments, 1)
        for investment in investments:
            ioc_last=ios_.io_current_last_operation_excluding_additions(investment.id)
            if ioc_last is None:
                continue
            ios_.d_data(investment.id)["last_datetime"]=ioc_last["datetime"]
            ios_.d_data(investment.id)["last_shares"]=ioc_last['shares']
            ios_.d_data(investment.id)["last_price"]=ioc_last['price_investment']
            ios_.d_data(investment.id)["percentage_last"]= ios_.d_total_io_current(investment.id)['percentage_total_user']
            ios_.d_data(investment.id)["percentage_invested"]= ioc_last["percentage_total_user"]
            ios_.d_data(investment.id)["percentage_sellingpoint"]=ios_.total_io_current_percentage_sellingpoint(investment.id, investment.selling_price).value
    elif method==1:#Merginc current operations
        ios_=ios.IOS.from_qs_merging_io_current( timezone.now(), request.user.profile.currency, investments, 1)
        for virtual_investment_product_id in ios_.entries(): #Products_id entries
            ioc_last=ios_.io_current_last_operation_excluding_additions(virtual_investment_product_id)            
            if ioc_last is None:
                continue
            #Añado valores calculados al data para utilizar ios_
            ios_.d_data(virtual_investment_product_id)["last_datetime"]=ioc_last["datetime"]
            ios_.d_data(virtual_investment_product_id)["last_shares"]=ioc_last['shares']
            ios_.d_data(virtual_investment_product_id)["last_price"]=ioc_last['price_investment']
            ios_.d_data(virtual_investment_product_id)["percentage_last"]= ios_.d_total_io_current(virtual_investment_product_id)['percentage_total_user']
            ios_.d_data(virtual_investment_product_id)["percentage_invested"]= ioc_last["percentage_total_user"]
            ios_.d_data(virtual_investment_product_id)["percentage_sellingpoint"]=None
    return JsonResponse( ios_.t(), encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportCurrentInvestmentsOperations(request):
    ld=[]
    investments=models.Investments.objects.filter(active=True).select_related("accounts","products")
    plio=ios.IOS.from_qs( timezone.now(), request.user.profile.currency, investments, 1)
    
    for inv in plio.qs_investments():
        for o in plio.d_io_current(inv.id):
            o["name"]=inv.fullName()
            ld.append(o)
    ld=lod.lod_order_by(ld, "datetime")
    
    return JsonResponse( ld, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportRanking(request):
    qs_investments=models.Investments.objects.all().select_related("products", "products__stockmarkets")
    ios_=ios.IOS.from_qs_merging_io_current( timezone.now(), request.user.profile.currency, qs_investments,  mode=ios.IOSModes.ios_totals_sumtotals)
    dividends=lod.lod2dod(models.Dividends.objects.all().values("investments__products__id").annotate(sum=Sum('net')), "investments__products__id")
    
    #Ranking generation
    lod_ranking=[]
    sum_dividends=Decimal(0)
    sum_total=Decimal(0)
    for products_id in ios_.entries():
        
        dividends_value=dividends[int(products_id)]["sum"]  if int(products_id) in dividends else 0
        total= ios_.d_total_io_current(products_id)["gains_net_user"]+ ios_.d_total_io_historical(products_id)["gains_net_user"] + dividends_value
        lod_ranking.append({
            "products_id": products_id, 
            "total": total, 
        })
        #Add dividend to data
        ios_.d_data(products_id)["dividends"]=dividends_value
        ios_.d_data(products_id)["total"]=total
        sum_dividends=sum_dividends+dividends_value
        sum_total=sum_total+total
    ios_.sum_total_io_historical()["sum_dividends"]=sum_dividends
    ios_.sum_total_io_historical()["sum_total"]=sum_total
    lod_ranking=lod.lod_order_by(lod_ranking, "total", reverse=True)
    for i,  d_rank in enumerate(lod_ranking):
        ios_.d_data(d_rank["products_id"])["ranking"]=i+1
    return JsonResponse(ios_._t, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportZeroRisk(request):
    qs=models.Investments.objects.filter(active=True, products__percentage=0).select_related("accounts",  "products", "products__productstypes","products__stockmarkets",  "products__leverages")
    plio=ios.IOS.from_qs(timezone.now(),  'EUR',  qs,  mode=ios.IOSModes.totals_sumtotals)        
    r=[]
    for o in qs:
        r.append({
            "id": o.id,
            "fullname":o.fullName(), 
            "url": o.hurl(request, o.pk), 
            "balance_user": plio.d_total_io_current(o.id)["balance_user"], 
            "currency": o.products.currency, 
            "flag": o.products.stockmarkets.country, 
            "decimals": o.decimals, 
        })
        
    
    qs_accounts=models.Accounts.objects.filter(active=True)
    r.append({
        "id": None,
        "fullname": _("Accounts total balance"), 
        "url": None, 
        "balance_user": models.Accounts.accounts_balance(qs_accounts, timezone.now(), 'EUR')["balance_user_currency"], 
        "currency": o.products.currency, 
        "flag": o.products.stockmarkets.country, 
        "decimals": o.decimals, 
    })
    return JsonResponse( r, encoder=myjsonencoder.MyJSONEncoderDecimalsAsFloat,     safe=False)

@api_view(['GET', ])
@permission_classes([permissions.IsAuthenticated, ])
def Statistics(request):
    r=[]
    for name, cls in ((_("Accounts"), models.Accounts), (_("Accounts operations"), models.Accountsoperations), (_("Banks"), models.Banks), (_("Concept"),  models.Concepts)):
        r.append({"name": name, "value":cls.objects.all().count()})
    return JsonResponse(r, safe=False)

class EstimationsDpsViewSet(viewsets.ModelViewSet):
    queryset = models.EstimationsDps.objects.all()
    serializer_class = serializers.EstimationsDpsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='product', description='Filter by product', required=False, type=OpenApiTypes.URI), 
        ],
    )
    def list(self, request):
        product=RequestUrl(self.request, "product", models.Products)
        if product is not None:
            self.queryset=self.queryset.filter(products=product).order_by("year")
        serializer = serializers.EstimationsDpsSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)

    
class StockmarketsViewSet(CatalogModelViewSet):
    queryset = models.Stockmarkets.objects.all()
    serializer_class = serializers.StockmarketsSerializer
    permission_classes = [permissions.IsAuthenticated]

class FastOperationsCoverageViewSet(viewsets.ModelViewSet):
    queryset = models.FastOperationsCoverage.objects.all().select_related("investments__products")
    serializer_class = serializers.FastOperationsCoverageSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='year', description='Filter by year', required=False, type=OpenApiTypes.INT), 
            OpenApiParameter(name='month', description='Filter by year', required=False, type=OpenApiTypes.INT), 
        ],
    )
    def list(self, request):
        year=RequestInteger(self.request, 'year')
        month=RequestInteger(self.request, 'month')
        if all_args_are_not_none(year, month):
            self.queryset= self.queryset.filter(datetime__year=year, datetime__month=month)
        serializer = serializers.FastOperationsCoverageSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)


class ProductsStrategiesViewSet(CatalogModelViewSet):
    queryset = models.ProductsStrategies.objects.all()
    serializer_class = serializers.ProductsStrategiesSerializer
    permission_classes = [permissions.IsAuthenticated]
