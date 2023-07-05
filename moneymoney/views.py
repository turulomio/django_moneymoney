from base64 import  b64encode, b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import prefetch_related_objects, Count, Sum, Q, Max, Subquery
from django.db.models.functions.datetime import ExtractMonth, ExtractYear
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from itertools import permutations
from math import ceil
from mimetypes import guess_extension
from moneymoney import models, serializers
from moneymoney.types import eComment, eConcept, eProductType, eOperationType
from moneymoney.reusing.connection_dj import execute, cursor_one_field, cursor_rows, cursor_rows_as_dict, show_queries, show_queries_function
from moneymoney.reusing.datetime_functions import dtaware_month_start,  dtaware_month_end, dtaware_year_end, string2dtaware, dtaware_year_start, months
from moneymoney.reusing.decorators import ptimeit
from moneymoney.reusing.percentage import Percentage,  percentage_between
from moneymoney.reusing.request_casting import RequestBool, RequestDate, RequestDecimal, RequestDtaware, RequestUrl, RequestGetString, RequestGetUrl, RequestGetBool, RequestGetInteger, RequestGetListOfIntegers, RequestGetDtaware, RequestListOfIntegers, RequestString, RequestListUrl, id_from_url, all_args_are_not_none, RequestCastingError
from moneymoney.reusing.responses_json import json_data_response, MyDjangoJSONEncoder, json_success_response
from moneymoney.reusing.sqlparser import sql_in_one_line
from requests import delete, post
from subprocess import run
from os import path
from pydicts import lod, lod_ymv
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from zoneinfo import available_timezones
from tempfile import TemporaryDirectory
from unogenerator.server import is_server_working

ptimeit, show_queries, show_queries_function

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
    return JsonResponse( request.user.groups.filter(name="CatalogManager").exists(), encoder=MyDjangoJSONEncoder, safe=False)


@extend_schema(
    parameters=[
        OpenApiParameter(name='outputformat', description='Output report format', required=True, type=str, default="pdf"), 
    ],
)
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def AssetsReport(request):
    """
        Generate user assets report
    """
    format_=RequestGetString(request, "outputformat", "pdf")
    if format_=="pdf":
        mime="application/pdf"
    elif format_=="odt":
        mime="application/vnd.oasis.opendocument.text"
    elif format_=="docx":
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        return Response({'status': 'Bad Format '}, status=status.HTTP_400_BAD_REQUEST)

    from moneymoney.assetsreport import generate_assets_report
    filename=generate_assets_report(request, format_)
    with open(filename, "rb") as pdf:
        encoded_string = b64encode(pdf.read())
        r={"filename":path.basename(filename),  "format": format_,  "data":encoded_string.decode("UTF-8"), "mime":mime}
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

    @action(detail=True, methods=['POST'], name='Transfer data from a concept to other', url_path="data_transfer", url_name='data_transfer', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def data_transfer(self, request, pk=None):
        concept_to=RequestUrl(request, "to", models.Concepts)
        if concept_to is not None:
            concept_from=self.get_object()
            execute("update accountsoperations set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
            execute("update creditcardsoperations set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
            execute("update dividends set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
            return Response({'status': 'details'}, status=status.HTTP_200_OK)
        return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["get"], name='Returns historical concept report', url_path="historical_report", url_name='historical_report', permission_classes=[permissions.IsAuthenticated])
    def historical_report(self, request, pk=None):
        concept= self.get_object()
        r={}
        json_concepts_historical=[]
        
        rows=cursor_rows("""
        select date_part('year',datetime)::int as year,  date_part('month',datetime)::int as month, sum(amount) as value 
        from ( 
                    SELECT accountsoperations.datetime, accountsoperations.concepts_id,  accountsoperations.amount  FROM accountsoperations where concepts_id={0} 
                        UNION ALL 
                    SELECT creditcardsoperations.datetime, creditcardsoperations.concepts_id, creditcardsoperations.amount FROM creditcardsoperations where concepts_id={0}
                ) as uni 
        group by date_part('year',datetime), date_part('month',datetime) order by 1,2 ;
        """.format(concept.id))

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
        
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    @action(detail=True, methods=["get"], name='Returns historical concept report detail', url_path="historical_report_detail", url_name='historical_report_detail', permission_classes=[permissions.IsAuthenticated])
    def ReportConceptsHistoricalDetail(self, request, pk=None):
        concept= self.get_object()
        year=RequestGetInteger(request, "year")
        month=RequestGetInteger(request, "month")
        if all_args_are_not_none(concept, year, month) is False:
            return Response({'status': 'year,month or concept is None'}, status=status.HTTP_400_BAD_REQUEST)
    
        qs_ao=models.Accountsoperations.objects.filter(concepts=concept, datetime__year=year, datetime__month=month)
        qs_cco=models.Creditcardsoperations.objects.filter(concepts=concept, datetime__year=year, datetime__month=month)
        
        data={
            "ao":  serializers.AccountsoperationsSerializer(qs_ao, many=True, context={'request': request}).data, 
            "cco":  serializers.CreditcardsoperationsSerializer(qs_cco, many=True, context={'request': request}).data, 
        }        
        return json_data_response(True, data,  "Ok")
        



class CreditcardsViewSet(viewsets.ModelViewSet):
    queryset = models.Creditcards.objects.select_related("accounts").all()
    serializer_class = serializers.CreditcardsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    def get_queryset(self):
        active=RequestGetBool(self.request, 'active')
        account_id=RequestGetInteger(self.request, 'account')

        if account_id is not None and active is not None:
            return self.queryset.filter(accounts_id=account_id,  active=active).order_by("name")
        elif active is not None:
            return self.queryset.filter(active=active).order_by("name")
        return self.queryset.order_by("name")

    @action(detail=False, methods=["get"], name='List creditcards with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):    
        r=[]
        for o in self.get_queryset():
            if o.deferred==False:
                balance=0
            else:
                balance=cursor_one_field("select coalesce(sum(amount),0) from creditcardsoperations where creditcards_id=%s and paid=false;", [o.id, ])
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

    @action(detail=True, methods=['GET'], name='Obtain historical payments of a credit card', url_path="payments", url_name='payments', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def payments(self, request, pk=None):
        creditcard=self.get_object()
        r=cursor_rows("""
            select 
                count(accountsoperations.id), 
                accountsoperations.id as accountsoperations_id, 
                accountsoperations.amount, 
                accountsoperations.datetime 
            from 
                accountsoperations, 
                creditcardsoperations 
            where 
                creditcardsoperations.accountsoperations_id=accountsoperations.id and 
                creditcards_id=%s and 
                accountsoperations.concepts_id=40 
            group by 
                accountsoperations.id, 
                accountsoperations.amount, 
                accountsoperations.datetime
            order by 
                accountsoperations.datetime
            """, (creditcard.id, ))
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)
        


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
            c.comment="Transaction in progress"
            c.save()
            c.comment=models.Comment().encode(eComment.CreditCardBilling, creditcard, c)
            c.save()

            #Modifica el registro y lo pone como paid y la datetime de pago y añade la opercuenta
            for o in qs_cco:
                o.paid_datetime=dt_payment
                o.paid=True
                o.accountsoperations_id=c.id
                o.save()
            return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
        return JsonResponse( False, encoder=MyDjangoJSONEncoder,     safe=False)
    

    

    @action(detail=True, methods=['GET'], name='Get a list of creditcards operations with balance', url_path="operationswithbalance", url_name='operationswithbalance', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def operationswithbalance(self, request, pk=None):   
        creditcard=self.get_object()
        paid=RequestGetBool(request, 'paid')
        if paid is not None:
            initial_balance=0
            qs=models.Creditcardsoperations.objects.select_related("creditcards", "concepts").filter(paid=paid, creditcards=creditcard).order_by("datetime")

        r=[]
        for o in qs:
            r.append({
                "id": o.id,  
                "url": request.build_absolute_uri(reverse('creditcardsoperations-detail', args=(o.pk, ))), 
                "datetime":o.datetime, 
                "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(o.concepts.pk, ))), 
                "amount": o.amount, 
                "balance":  initial_balance + o.amount, 
                "comment": models.Comment().decode(o.comment), 
                "creditcards":request.build_absolute_uri(reverse('creditcards-detail', args=(o.creditcards.pk, ))), 
                "paid": o.paid, 
                "paid_datetime": o.paid_datetime, 
                "currency": o.creditcards.accounts.currency, 
            })
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)



class CreditcardsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Creditcardsoperations.objects.all().select_related("creditcards").select_related("creditcards__accounts")
    serializer_class = serializers.CreditcardsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
        
    def get_queryset(self):
        ##Saca los pagos hechos en esta operación de cuenta
        accountsoperations_id=RequestGetInteger(self.request, 'accountsoperations_id')
        if accountsoperations_id is not None:
            return self.queryset.filter(accountsoperations__id=accountsoperations_id)
        else:
            return self.queryset.all()


    
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)        

class DividendsViewSet(viewsets.ModelViewSet):
    queryset = models.Dividends.objects.all().select_related("investments", "investments__accounts")
    serializer_class = serializers.DividendsSerializer
    permission_classes = [permissions.IsAuthenticated] 
    
    
    ## To use this methos use axios 
    ##            var headers={...this.myheaders(),params:{investments: [1,2,3],otra:"OTTRA"}}
    ##            return axios.get(`${this.$store.state.apiroot}/api/dividends/`, headers)
    def get_queryset(self):
        investments_ids=RequestGetListOfIntegers(self.request,"investments[]") 
        datetime=RequestGetDtaware(self.request, 'from', self.request.user.profile.zone)
        if len(investments_ids)>0 and datetime is None:
            return self.queryset.filter(investments__in=investments_ids).order_by("datetime")
        elif len(investments_ids)>0 and datetime is not None:
            return self.queryset.filter(investments__in=investments_ids,  datetime__gte=datetime).order_by("datetime")
        else:
            return self.queryset.order_by("datetime")
    
    
class DpsViewSet(viewsets.ModelViewSet):
    queryset = models.Dps.objects.all()
    serializer_class = serializers.DpsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    def get_queryset(self):
        try:
            product=RequestGetUrl(self.request, 'product', models.Products)
        except RequestCastingError as e:
            print(e)
            return self.queryset.none()
        if all_args_are_not_none(product):
            return self.queryset.filter(products=product)
        return self.queryset

class OrdersViewSet(viewsets.ModelViewSet):
    queryset = models.Orders.objects.select_related("investments","investments__accounts","investments__products","investments__products__productstypes","investments__products__leverages").all()
    serializer_class = serializers.OrdersSerializer
    permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        active=RequestGetBool(self.request, 'active')
        expired=RequestGetBool(self.request, 'expired')
        expired_days=RequestGetInteger(self.request, 'expired_days')
        executed=RequestGetBool(self.request, 'executed')
        if active is not None:
            return self.queryset.filter(Q(expiration__gte=date.today()) | Q(expiration__isnull=True), executed__isnull=True)
        elif expired is not None:
            return self.queryset.filter(expiration__lte=date.today(),  executed__isnull=True)
        elif expired_days is not None:
            """
                Returns orders that have expired in last expired_days and that haven't been reordered. Used to alert expired orders
            """
            qs_orders_expired_days=self.queryset.filter(expiration__range=(date.today()-timedelta(days=expired_days), date.today()),  executed__isnull=True)

            set_investments_with_orders_active=set(models.Orders.objects.filter(Q(expiration__gte=date.today()) | Q(expiration__isnull=True), executed__isnull=True).values_list("investments_id", flat=True))
            set_investments_with_orders_expired_days=set(qs_orders_expired_days.values_list("investments_id", flat=True))
            set_investments_with_orders_not_reorderd=set_investments_with_orders_expired_days-set_investments_with_orders_active
            print(set_investments_with_orders_active, set_investments_with_orders_expired_days, set_investments_with_orders_not_reorderd)
            return qs_orders_expired_days.filter(investments_id__in=list(set_investments_with_orders_not_reorderd))
        elif executed is not None:
            return self.queryset.filter(executed__isnull=False)
        else:
            return self.queryset

    def list(self, request):  
        r=[]
        for o in self.get_queryset():
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

class OperationstypesViewSet(CatalogModelViewSet):
    queryset = models.Operationstypes.objects.all()
    serializer_class = serializers.OperationstypesSerializer

class StrategiesViewSet(viewsets.ModelViewSet):
    queryset = models.Strategies.objects.all()
    serializer_class = serializers.StrategiesSerializer
    permission_classes = [permissions.IsAuthenticated]  
        
    @extend_schema(
        parameters=[
            OpenApiParameter(name='active', description='Filter by active accounts', required=True, type=bool), 
            OpenApiParameter(name='investment', description='Filter by investment', required=True, type=OpenApiTypes.URI), 
            OpenApiParameter(name='type', description='Filter by type', required=True, type=int), 
        ],
    )
    def list(self, request):
        active=RequestGetBool(request, "active")
        investment=RequestGetUrl(request, "investment", models.Investments)
        type=RequestGetInteger(request, "type")
        if all_args_are_not_none(active, investment, type):
            self.queryset=self.queryset.filter(dt_to__isnull=active,  investments__contains=investment.id, type=type)
        serializer = serializers.StrategiesSerializer(self.queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], name='List investments with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request): 
        active=RequestGetBool(request, 'active')
        if active is None:
            qs=models.Strategies.objects.all() 
        else:
            if active is True:
                qs=models.Strategies.objects.filter(dt_to__isnull=True)
            else:
                qs=models.Strategies.objects.filter(dt_to__isnull=False)

        r=[]
        for strategy in qs:
            dividends_net_user=0
            plio=models.PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, strategy.investments_queryset(), 1)

            gains_current_net_user=plio.sum_total_io_current()["gains_net_user"]
            gains_historical_net_user=plio.io_historical_sum_between_dt(strategy.dt_from, strategy.dt_to_for_comparations(),  "gains_net_user")
            lod_dividends_net_user=models.Dividends.lod_ym_netgains_dividends(request, ids=strategy.investments_ids(), dt_from=strategy.dt_from, dt_to=strategy.dt_to_for_comparations())
            r.append({
                "id": strategy.id,  
                "url": request.build_absolute_uri(reverse('strategies-detail', args=(strategy.pk, ))), 
                "name":strategy.name, 
                "dt_from": strategy.dt_from, 
                "dt_to": strategy.dt_to, 
                "invested": plio.sum_total_io_current()["invested_user"], 
                "gains_current_net_user":  gains_current_net_user,  
                "gains_historical_net_user": gains_historical_net_user, 
                "dividends_net_user": lod.lod_sum(lod_dividends_net_user, "total"), 
                "total_net_user":gains_current_net_user + gains_historical_net_user + dividends_net_user, 
                "investments":strategy.investments_ids(), 
                "type": strategy.type, 
                "comment": strategy.comment, 
                "additional1": strategy.additional1, 
                "additional2": strategy.additional2, 
                "additional3": strategy.additional3, 
                "additional4": strategy.additional4, 
                "additional5": strategy.additional5, 
                "additional6": strategy.additional6, 
                "additional7": strategy.additional7, 
                "additional8": strategy.additional8, 
                "additional9": strategy.additional9, 
                "additional10": strategy.additional10, 
            })
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)
        
    @action(detail=True, methods=["get"], name='Gets a plio_id from strategy investments', url_path="plio_id", url_name='plio_id', permission_classes=[permissions.IsAuthenticated])
    def plio_id(self, request, pk=None): 
        strategy=self.get_object()
        if strategy is not None:
            s=models.PlInvestmentOperations.plio_id_from_strategy(timezone.now(), request.user.profile.currency, strategy)
            return JsonResponse( s, encoder=MyDjangoJSONEncoder,  safe=False)
        return Response({'status': _('Strategy was not found')}, status=status.HTTP_404_NOT_FOUND)


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
            for mode, name in (('p', 'Put'), ('c', 'Call'), ('i', 'Inline')):
                d={"name": name, "balance": 0,  "invested": 0}
                for investment in qs_investments_active:
                    if investment.products.pci==mode:
                        d["balance"]=d["balance"]+plio.d_total_io_current(investment.id)["balance_user"]
                        d["invested"]=d["invested"]+plio.d_total_io_current(investment.id)["invested_user"]
                if mode=="c":
                    d["balance"]=d["balance"]+accounts_balance
                    d["invested"]=d["invested"]+accounts_balance
                ld.append(d)
            
            return ld



        def json_classes_by_product():
            ld=[]
            for product in models.Products.objects.order_by().distinct("investments__products").select_related("stockmarkets"):
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
        accounts_balance=models.Accounts.balance_user_currency(models.Accounts.objects.filter(active=True), timezone.now())
        qs_investments_active=models.Investments.objects.filter(active=True).select_related("products","products__productstypes","accounts","products__leverages")

        plio=models.PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, qs_investments_active,  1)

        d={}
        d["by_leverage"]=json_classes_by_leverage()
        d["by_pci"]=json_classes_by_pci()
        d["by_percentage"]=json_classes_by_percentage()
        d["by_product"]=json_classes_by_product()
        d["by_producttype"]=json_classes_by_producttype()
        
        return JsonResponse( d, encoder=MyDjangoJSONEncoder,     safe=False)

class UnogeneratorWorking(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        description="Returns if unogenerator server is working", 
        request=None, 
        responses=OpenApiTypes.OBJECT
    )
    def get(self, request, *args, **kwargs):
        if is_server_working():
            return json_success_response(True, _("Unogenerator server is working") )
        else:
            return json_success_response(False, _("Unogenerator server is not working") )

class Alerts(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(request=None, responses=OpenApiTypes.DATETIME)
    def get(self, request, *args, **kwargs):
        r={}
        r["server_time"]=timezone.now()
        
        #Expired orders calling other viewset from this viewsets
        r["expired_days"]=7
        r["orders_expired"]=models.request_get(request._request.build_absolute_uri(reverse('orders-list'))+f"?expired_days={r['expired_days']}", request.user.auth_token.key)
        
        
        # Get all inactive accounts status
        r["accounts_inactive_with_balance"]=[]
        lod_accounts=models.request_get(request._request.build_absolute_uri(reverse('accounts-list'))+"withbalance/?active=false", request.user.auth_token.key)
        for d in lod_accounts:
            if d["balance_account"]!=0:
                r["accounts_inactive_with_balance"].append(d)

        # Get all investments status
        r["investments_inactive_with_balance"]=[]
        qs=models.Investments.objects.filter(active=False)
        plio_inactive=models.PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, qs,  2)
        for id in plio_inactive.list_investments_id():
            plio=plio_inactive.d(id)
            if plio["total_io_current"]["balance_investment"]!=0:
                r["investments_inactive_with_balance"].append(plio)
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

class Timezones(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(request=None, responses=OpenApiTypes.STR)
    def get(self, request, *args, **kwargs):
        r=list(available_timezones())
        r.sort()
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)


class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = models.Investments.objects.select_related("accounts").all()
    serializer_class = serializers.InvestmentsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_queryset(self):
        # To get active or inactive accounts
        active=RequestGetBool(self.request, "active")
        bank_id=RequestGetInteger(self.request,"bank")

        if bank_id is not None:
            return self.queryset.filter(accounts__banks__id=bank_id,  active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset

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
        start=datetime.now()
        
        
        ### DELETE MemoryError
        #print("AHORA", models.Assets.pl_investment_operations(timezone.now(), request.user.profile.currency, [69, ],  1))
        #######
        

        
        plio=models.PlInvestmentOperations.from_ids(timezone.now(),  'EUR',  None,  mode=2)
        r=[]
        for o in self.get_queryset().select_related("accounts",  "products", "products__productstypes","products__stockmarkets",  "products__leverages"):
            percentage_invested=None if plio.d_total_io_current(o.id)["invested_user"]==0 else  plio.d_total_io_current(o.id)["gains_gross_user"]/plio.d_total_io_current(o.id)["invested_user"]
            try:                
                last_day_diff= (o.products.basic_results()['last']-o.products.basic_results()['penultimate'])*plio.d_total_io_current(o.id)["shares"]*o.products.real_leveraged_multiplier()
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
                "last_datetime": o.products.basic_results()['last_datetime'], 
                "last": o.products.basic_results()['last'], 
                "daily_difference": last_day_diff, 
                "daily_percentage":percentage_between(o.products.basic_results()['penultimate'], o.products.basic_results()['last']), 
                "invested_user": plio.d_total_io_current(o.id)["invested_user"], 
                "gains_user": plio.d_total_io_current(o.id)["gains_gross_user"], 
                "balance_user": plio.d_total_io_current(o.id)["balance_user"], 
                "currency": o.products.currency, 
                "currency_account": o.accounts.currency, 
                "percentage_invested": percentage_invested, 
                "percentage_selling_point": percentage_to_selling_point(plio.d_total_io_current(o.id)["shares"], o.selling_price, o.products.basic_results()['last']), 
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
        print(datetime.now()-start, "balance")
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

    @action(detail=True, methods=["get"], name='Investments operations evolution chart', url_path="operations_evolution_chart", url_name='operations_evolution_chart', permission_classes=[permissions.IsAuthenticated])
    def operations_evolution_chart(self, request, pk=None):
        investment=self.get_object()
        plio=models.PlInvestmentOperations.from_ids(timezone.now(), request.user.profile.currency, [investment.id, ], 1)
        if len(plio.d_io(investment.id))==0:
            return JsonResponse( _("Insuficient data") , encoder=MyDjangoJSONEncoder, safe=False)
        
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
            plio_dt=models.PlInvestmentOperations.from_ids(dt, request.user.profile.currency, [investment.id, ], 2)
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
        return JsonResponse( d, encoder=MyDjangoJSONEncoder, safe=False)

class InvestmentsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Investmentsoperations.objects.select_related("investments").select_related("investments__products").all()
    serializer_class = serializers.InvestmentsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.investments.set_attributes_after_investmentsoperations_crud()
        return Response(status=status.HTTP_204_NO_CONTENT)    

@api_view(['POST', 'PUT', 'DELETE' ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def AccountTransfer(request): 
    account_origin=RequestUrl(request, 'account_origin', models.Accounts)#Returns an account object
    account_destiny=RequestUrl(request, 'account_destiny', models.Accounts)
    datetime=RequestDtaware(request, 'datetime', request.user.profile.zone)
    amount=RequestDecimal(request, 'amount')
    commission=RequestDecimal(request, 'commission',  0)
    ao_origin=RequestUrl(request, 'ao_origin', models.Accountsoperations)
    ao_destiny=RequestUrl(request, 'ao_destiny', models.Accountsoperations)
    ao_commission=RequestUrl(request, 'ao_commission', models.Accountsoperations)
    if request.method=="POST":
        if ( account_destiny is not None and account_origin is not None and datetime is not None and amount is not None and amount >=0 and commission is not None and commission >=0 and account_destiny!=account_origin):
            if commission >0:
                ao_commission=models.Accountsoperations()
                ao_commission.datetime=datetime
                concept_commision=models.Concepts.objects.get(pk=eConcept.BankCommissions)
                ao_commission.concepts=concept_commision
                ao_commission.amount=-commission
                ao_commission.accounts=account_origin
                ao_commission.save()

            #Origin
            ao_origin=models.Accountsoperations()
            ao_origin.datetime=datetime
            concept_transfer_origin=models.Concepts.objects.get(pk=eConcept.TransferOrigin)
            ao_origin.concepts=concept_transfer_origin
            ao_origin.amount=-amount
            ao_origin.accounts=account_origin
            ao_origin.save()

            #Destiny
            ao_destiny=models.Accountsoperations()
            ao_destiny.datetime=datetime
            concept_transfer_destiny=models.Concepts.objects.get(pk=eConcept.TransferDestiny)
            ao_destiny.concepts=concept_transfer_destiny
            ao_destiny.amount=amount
            ao_destiny.accounts=account_destiny
            ao_destiny.save()

            #Encoding comments
            ao_origin.comment=models.Comment().encode(eComment.AccountTransferOrigin, ao_origin, ao_destiny, ao_commission)
            ao_origin.save()
            ao_destiny.comment=models.Comment().encode(eComment.AccountTransferDestiny, ao_origin, ao_destiny, ao_commission)
            ao_destiny.save()
            if ao_commission is not None:
                ao_commission.comment=models.Comment().encode(eComment.AccountTransferOriginCommission, ao_origin, ao_destiny, ao_commission)
                ao_commission.save()
            return JsonResponse( True,  encoder=MyDjangoJSONEncoder,     safe=False)
        else:
            return Response({'status': 'Something wrong adding an account transfer'}, status=status.HTTP_400_BAD_REQUEST)    
    if request.method=="PUT": #Update
        ## I use the same code deleting y posting. To avoid errors or accounts operations zombies.
        delete(request.build_absolute_uri(), headers = {"Authorization": request.headers["Authorization"], },  data=request.data, verify=False)
        post(request.build_absolute_uri(), headers = {"Authorization": request.headers["Authorization"], },  data=request.data, verify=False)
        print("This should check cert or try with drf internals")
        return JsonResponse( True,  encoder=MyDjangoJSONEncoder,     safe=False)
    if request.method=="DELETE":
        if ao_destiny is not None and ao_origin is not None:
            if ao_commission is not None:
                ao_commission.delete()
            ao_destiny.delete()
            ao_origin.delete()
            return Response({'status': 'details'}, status=status.HTTP_200_OK)
        return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)  

class AccountsViewSet(viewsets.ModelViewSet):
    queryset = models.Accounts.objects.select_related("banks").all()
    serializer_class = serializers.AccountsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    def get_queryset(self):
        active=RequestGetBool(self.request, 'active')
        bank_id=RequestGetInteger(self.request, 'bank')

        if bank_id is not None:
            return self.queryset.filter(banks__id=bank_id,   active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
        return self.queryset

    @action(detail=False, methods=["get"], name='List accounts with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):
        r=[]
        for o in self.get_queryset():
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

            

    @action(detail=True, methods=["get"], name='List accounts operations with balance calculations of an account', url_path="monthoperations", url_name='monthoperations', permission_classes=[permissions.IsAuthenticated])
    def monthoperations(self, request, pk=None):
        account=self.get_object()
        year=RequestGetInteger(request, 'year')
        month=RequestGetInteger(request, 'month')
        
        if all_args_are_not_none( year, month):
            dt_initial=dtaware_month_start(year, month, request.user.profile.zone)
            initial_balance=account.balance( dt_initial, request.user.profile.currency)[0]
            qs=models.Accountsoperations.objects.select_related("accounts","concepts").filter(datetime__year=year, datetime__month=month, accounts=account).order_by("datetime")

            r=[]
            for o in qs:
                r.append({
                    "id": o.id,  
                    "url": request.build_absolute_uri(reverse('accountsoperations-detail', args=(o.pk, ))), 
                    "datetime":o.datetime, 
                    "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(o.concepts.pk, ))), 
                    "amount": o.amount, 
                    "balance":  initial_balance + o.amount, 
                    "comment": o.comment, 
                    "comment_decoded": models.Comment().decode(o.comment), 
                    "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.pk, ))), 
                    "currency": o.accounts.currency, 
                    "is_editable": o.is_editable(), 
                })
                initial_balance=initial_balance + o.amount
            return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)
        return JsonResponse( "Some parameters are missing", encoder=MyDjangoJSONEncoder, safe=False)

class AccountsoperationsViewSet(viewsets.ModelViewSet):
    queryset = models.Accountsoperations.objects.select_related("accounts").all()
    serializer_class = serializers.AccountsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    def get_queryset(self):
        search=RequestGetString(self.request, 'search')
        concept=RequestGetUrl(self.request, 'concept', models.Concepts)
        year=RequestGetInteger(self.request, 'year')
        month=RequestGetInteger(self.request, 'month')

        if search is not None:
            return self.queryset.filter(comment__icontains=search)
        if all_args_are_not_none(concept, year, month):
            return self.queryset.filter(concepts=concept, datetime__year=year, datetime__month=month)
        if all_args_are_not_none(concept, year):
            return self.queryset.filter(concepts=concept, datetime__year=year)
        return self.queryset

    @action(detail=True, methods=['POST'], name='Refund all cco paid in an ao', url_path="ccpaymentrefund", url_name='ccpaymentrefund', permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def ccpaymentrefund(self, request, pk=None):
        ao=self.get_object()
        models.Creditcardsoperations.objects.filter(accountsoperations_id=ao.id).update(paid_datetime=None,  paid=False, accountsoperations_id=None)
        ao.delete() #Must be at the end due to middle queries
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
            
class BanksViewSet(viewsets.ModelViewSet):
    queryset = models.Banks.objects.all()
    permission_classes = [permissions.IsAuthenticated]  
    serializer_class =  serializers.BanksSerializer

    def get_queryset(self):
        active=RequestGetBool(self.request, "active")
        if active is not None:
            return self.queryset.filter(active=active)
        return self.queryset


    @action(detail=False, methods=["get"], name='List banks with balance calculations', url_path="withbalance", url_name='withbalance', permission_classes=[permissions.IsAuthenticated])
    def withbalance(self, request):
        r=[]
        for o in self.get_queryset():
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
        



@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFull(request):
    """
        This view returns a simulated plio_id
    """
    ids=RequestGetListOfIntegers(request, "investments[]")
    mode=RequestGetInteger(request, "mode", 1)
    plio=models.PlInvestmentOperations.from_ids(timezone.now(), request.user.profile.currency, ids, mode)
    return JsonResponse( plio.t(), encoder=MyDjangoJSONEncoder, safe=False)


@api_view(['POST', ]) 
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFullSimulation(request):
    """
        It uses plio_id io_current o make simulation
        Using plio_id I can simulate, merged plios, or investments_plios  or even other simulations, but only one. That's the reason  of plio_id not plio.
    """
    plio_id=request.data["plio_id"]
    # Request returns datetime as JsUtcISO. I must convert them to dtaware
    plio_id["data"]["dt"]=string2dtaware(plio_id["data"]["dt"],  "JsUtcIso", request.user.profile.zone)
    for o in plio_id["io_current"]:
        o["datetime"]=string2dtaware(o["datetime"],  "JsUtcIso", request.user.profile.zone)
        #Ioc current doesn't have price
        o["shares"]=Decimal(o["shares"])
        o["price"]=Decimal(o["price_investment"])
        o["taxes"]=Decimal(o["taxes_account"])
        o["commission"]=Decimal(o["commissions_account"])
        o["currency_conversion"]=Decimal(o["investment2account"])
        
    listdict=request.data["operations"]
    lod_ios_to_simulate=[]
    for i,  d in enumerate(listdict):
        lod_ios_to_simulate.append({
                "id":-i, 
                "operationstypes_id": id_from_url(d["operationstypes"]), 
                "shares": Decimal(d["shares"]), 
                "taxes": Decimal(d["taxes"]), 
                "commission": Decimal(d["commission"]), 
                "price": Decimal(d["price"]), 
                "datetime": string2dtaware(d["datetime"],  "JsUtcIso", request.user.profile.zone), 
                "currency_conversion":Decimal(d["currency_conversion"]), 
                "investments_id":plio_id["data"]["investments_id"]
        })
    lod_data=[plio_id["data"], ] #It's an array
    lod_all=plio_id["io_current"] + lod_ios_to_simulate
    plio_id_after=models.PlInvestmentOperations.plio_id_from_virtual_investments_simulation(plio_id["data"]["dt"],  request.user.profile.currency, lod_data, lod_all, 1)
    return JsonResponse( plio_id_after, encoder=MyDjangoJSONEncoder,safe=False)






@transaction.atomic
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsChangeSellingPrice(request):
    selling_price=RequestDecimal(request, "selling_price")
    selling_expiration=RequestDate(request, "selling_expiration")
    investments=RequestListUrl(request, "investments", models.Investments)
    ids=[]
    if investments is not None and selling_price is not None: #Pricce 
        with transaction.atomic():
            for inv in investments:
                ids.append(inv.id)
                inv.selling_price=selling_price
                inv.selling_expiration=selling_expiration
                inv.save()
        r   = serializers.InvestmentsSerializer(models.Investments.objects.filter(id__in=ids), many=True, context={'request': request}).data
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
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
    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

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
    product_better=RequestGetUrl(request, "a", models.Products)
    product_worse=RequestGetUrl(request, "b", models.Products)
    interval_minutes=RequestGetInteger(request, "interval_minutes", 1)
    
    common_quotes=cursor_rows("""
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
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@api_view(['GET', 'DELETE' ])    
@permission_classes([permissions.IsAuthenticated, ])
## GET METHODS
## products/quotes/ohcl/?product_url To get all ohcls of a product
## products/quotes/ohcl/?product_url&year=2022&month=4 To get ochls of a product, in a month
## DELETE METHODS
## products/quotes/ohcl?product=url&date=2022-4-1
def ProductsQuotesOHCL(request):
    if request.method=="GET":
        product=RequestGetUrl(request, "product", models.Products)
        year=RequestGetInteger(request, "year")
        month=RequestGetInteger(request, "month")
        
        if product is not None and year is not None and month is not None:
            ld_ohcl=product.ohclDailyBeforeSplits()       
            r=[] ## TODO. Add from_date in postgres function to avoid this
            for d in ld_ohcl:
                if d["date"].year==year and d["date"].month==month:
                    r.append(d)
            return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

        if product is not None:
            ld_ohcl=product.ohclDailyBeforeSplits()         
            return JsonResponse( ld_ohcl, encoder=MyDjangoJSONEncoder, safe=False)
            
    elif request.method=="DELETE":
        product=RequestUrl(request, "product", models.Products)
        date=RequestDate(request, "date")
        if product is not None and date is not None:
            qs=models.Quotes.objects.filter(products=product, datetime__date=date)
            qs.delete()
            return JsonResponse(True, encoder=MyDjangoJSONEncoder, safe=False)

    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsRanges(request):
    product=RequestGetUrl(request, "product", models.Products)
    totalized_operations=RequestGetBool(request, "totalized_operations") 
    percentage_between_ranges=RequestGetInteger(request, "percentage_between_ranges")

    if percentage_between_ranges is not None:
        percentage_between_ranges=percentage_between_ranges/1000
    percentage_gains=RequestGetInteger(request, "percentage_gains")
    if percentage_gains is not None:
        percentage_gains=percentage_gains/1000
    amount_to_invest=RequestGetInteger(request, "amount_to_invest")
    recomendation_methods=RequestGetInteger(request, "recomendation_methods")
    investments_ids=RequestGetListOfIntegers(request,"investments[]") 
    if len(investments_ids)>0:
        qs_investments=models.Investments.objects.filter(id__in=investments_ids)
    else:
        qs_investments=models.Investments.objects.none()
    additional_ranges=RequestGetInteger(request, "additional_ranges", 3)

    if all_args_are_not_none(product, totalized_operations,  percentage_between_ranges, percentage_gains, amount_to_invest, recomendation_methods):
        from moneymoney.productrange import ProductRangeManager
        
        prm=ProductRangeManager(request, product, percentage_between_ranges, percentage_gains, totalized_operations,  qs_investments=qs_investments, decimals=product.decimals, additional_ranges=additional_ranges)
        prm.setInvestRecomendation(recomendation_methods)

        return JsonResponse( prm.json(), encoder=MyDjangoJSONEncoder, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)
    
    
## Has annotate investments__count en el queryset
## Solo afectaría a personal products<0. Solo investments, ya que todas las demás dependen de produto y habría que borrarllas
## Es decir si borro un producto, borraría quotes, splits, estimatiosn.....
class ProductsViewSet(viewsets.ModelViewSet):
    queryset = models.Products.objects.select_related("productstypes","leverages", "stockmarkets").all().annotate(uses=Count('investments', distinct=True))
    serializer_class = serializers.ProductsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if  request.user.groups.filter(name="CatalogManager").exists() and instance.id>0:
            return JsonResponse( "Error deleting system product", encoder=MyDjangoJSONEncoder,     safe=False)
    
        self.perform_destroy(instance)
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)

    @action(detail=True, methods=['POST'], name='Delete last quote of the product', url_path="delete_last_quote", url_name='delete_last_quote', permission_classes=[permissions.IsAuthenticated])
    def delete_last_quote(self, request, pk=None):
        product = self.get_object()
        instance = models.Quotes.objects.filter(products=product).order_by("-datetime")[0]
        self.perform_destroy(instance)
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
        

    @action(detail=False, methods=["GET"], url_path='search_with_quotes', url_name='search_with_quotes')
    def search_with_quotes(self, request, *args, **kwargs):
        """
            Search products and return them with last, penultimate, and last year quotes
        """
        def db_query_by_products_ids(ids):
            return cursor_rows(sql_in_one_line("""
                select 
                    products.id, 
                    last_datetime, 
                    last, 
                    penultimate_datetime, 
                    penultimate, 
                    lastyear_datetime, 
                    lastyear 
                from 
                    products,
                    last_penultimate_lastyear(products.id, now()) 
                where 
                    products.id = any(%s)
            """), (ids, ))
        #############################################        
        search=RequestGetString(request, "search")
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
            rows=db_query_by_products_ids(ids) if len(ids)>0 else []
            for row in rows:
                row["product"]=request.build_absolute_uri(reverse('products-detail', args=(row['id'], )))
                row["percentage_last_year"]=None if row["lastyear"] is None else Percentage(row["last"]-row["lastyear"], row["lastyear"])
            return json_data_response(True, rows, "Products search done")
        return json_data_response(False, rows, "Products search error")

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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

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
    
            ic=InvestingCom(request, product=None)
            ic.load_from_filename_in_disk(f"{tmp}/portfolio.csv")
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

        ic=InvestingCom(request, product=None)
        ic.load_from_filename_in_memory(csv_file)
    r=ic.get()
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)
        
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
        return json_data_response( True, r,  "Quotes massive update success")
 
class QuotesViewSet(viewsets.ModelViewSet):
    queryset = models.Quotes.objects.all().select_related("products")
    serializer_class = serializers.QuotesSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    ## api/quotes/ Show all quotes of the database
    ## api/quotes/?future=true Show all quotes with datetime in the future for debugging
    ## api/quotes/?last=true Shows all products last Quotes
    ## api/quotes/?product=url Showss all quotes of a product
    ## api/quotes/?product=url&month=1&year=2021 Showss all quotes of a product in a month
    def get_queryset(self):
        product=RequestGetUrl(self.request, 'product', models.Products)
        future=RequestGetBool(self.request, 'future')
        last=RequestGetBool(self.request, 'last')
        month=RequestGetInteger(self.request, 'month')
        year=RequestGetInteger(self.request, 'year')
        
        if future is True:
            return models.Quotes.objects.all().filter(datetime__gte=timezone.now()).select_related("products").order_by("datetime")
                
        ## Search last quote of al linvestments
        if last is True:
            qs=models.Quotes.objects.raw("""
                select 
                    id, 
                    quotes.products_id, 
                    quotes.datetime, 
                    quote 
                from 
                    quotes, 
                    (select max(datetime) as datetime, products_id from quotes group by products_id) as maxdt 
                where 
                    quotes.products_id=maxdt.products_id and 
                    quotes.datetime=maxdt.datetime 
                order by 
                    quotes.datetime desc
            """)
            #Querysets with raw sql can use select_related, but with one more query you can use this
            prefetch_related_objects(qs, 'products')
            return qs

        if all_args_are_not_none(product, year, month):
            return self.queryset.filter(products=product, datetime__year=year, datetime__month=month).order_by("datetime")
        if product is not None:
            return self.queryset.filter(products=product).order_by("datetime")

        return self.queryset


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
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportAnnual(request, year):
    def month_results(month_end, month_name, local_currency):
        return month_end, month_name, models.Assets.pl_total_balance(month_end, local_currency)
        
    #####################
    
    dtaware_last_year=dtaware_year_end(year-1, request.user.profile.zone)
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
        month_end=dtaware_month_end(year, month, request.user.profile.zone)
        future= month_results(month_end,  month_name, request.user.profile.currency)
        futures.append(future)

    futures= sorted(futures, key=lambda future: future[0])#month_end
    last_month=last_year['total_user']
    for future in futures:
        month_end, month_name,  total = future
        list_.append({
            "month_number":month_end, 
            "month": month_name,
            "account_balance":total['accounts_user'], 
            "investment_balance":total['investments_user'], 
            "total":total['total_user'] , 
            "percentage_year": percentage_between(last_year['total_user'], total['total_user'] ), 
            "diff_lastmonth": total['total_user']-last_month, 
        })
        last_month=total['total_user']
        
    r={"last_year_balance": last_year['total_user'],  "dtaware_last_year": dtaware_last_year,  "data": list_}
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
 
 


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportAnnualIncome(request, year):
    list_=[]
    dt_year_from=dtaware_year_start(year, request.user.profile.zone)
    dt_year_to=dtaware_year_end(year, request.user.profile.zone)
    
    plio=models.PlInvestmentOperations.from_all(dt_year_to, request.user.profile.currency, 1)
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request, dt_from=dt_year_from, dt_to=dt_year_to), "year")
    d_incomes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Income, year=year), "year")
    d_expenses=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Expense, year=year), "year")
    d_fast_operations=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.FastOperations, year=year), "year")

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
        dividends= d_dividends[year][f"m{month}"]  if year in d_dividends else 0
        incomes=d_incomes[year][f"m{month}"] if year in d_incomes else 0 -dividends
        expenses=d_expenses[year][f"m{month}"] if year in d_expenses else 0
        fast_operations=d_fast_operations[year][f"m{month}"] if year in d_fast_operations else 0
        dt_from=dtaware_month_start(year, month,  request.user.profile.zone)
        dt_to=dtaware_month_end(year, month,  request.user.profile.zone)
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
    
    return JsonResponse( list_, encoder=MyDjangoJSONEncoder, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncomeDetails(request, year, month):
    def listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, operationstypes_id, local_currency, local_zone):
        # Expenses
        r=[]
        balance=0
        for currency in models.Accounts.currencies():
            for i,  op in enumerate(cursor_rows("""
                select 
                    datetime,
                    concepts_id, 
                    amount, 
                    comment, 
                    accounts.id as accounts_id
                from 
                    accountsoperations,
                    accounts,
                    concepts
                where 
                    concepts.operationstypes_id=%s and 
                    date_part('year',datetime)=%s and
                    date_part('month',datetime)=%s and
                    accounts.currency=%s and
                    accounts.id=accountsoperations.accounts_id and
                    accountsoperations.concepts_id=concepts.id
            union all 
                select datetime,concepts_id, amount, comment, accounts.id as accounts_id
                from 
                    creditcardsoperations ,
                    creditcards,
                    accounts,
                    concepts
                where 
                    concepts.operationstypes_id=%s and 
                    date_part('year',datetime)=%s and
                    date_part('month',datetime)=%s and
                    accounts.currency=%s and
                    accounts.id=creditcards.accounts_id and
                    creditcards.id=creditcardsoperations.creditcards_id and
                    creditcardsoperations.concepts_id=concepts.id
                """, (operationstypes_id, year, month,  currency, operationstypes_id, year, month,  currency))):
                if local_currency==currency:
                    balance=balance+op["amount"]
                    r.append({
                        "id":-i, 
                        "datetime": op['datetime'], 
                        "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(op["concepts_id"], ))), 
                        "amount":op['amount'], 
                        "balance": balance,
                        "comment_decoded":models.Comment().decode(op["comment"]), 
                        "currency": currency, 
                        "accounts": request.build_absolute_uri(reverse('accounts-detail', args=(op["accounts_id"], ))), 
                    })
                else:
                    print("TODO")
                
            r= sorted(r,  key=lambda item: item['datetime'])
    #            r=r+money_convert(dtaware_month_end(year, month, local_zone), balance, currency, local_currency)
        return r
    def dividends():
        #TODO: Should use all currencies
        qs=models.Dividends.objects.filter(datetime__year=year, datetime__month=month).order_by('datetime').select_related("investments").select_related("investments__accounts")
        return serializers.DividendsSerializer(qs, many=True, context={'request': request}).data
    def listdict_investmentsoperationshistorical(request, year, month, local_currency, local_zone):
        list_ioh=[]
        dt_year_month=dtaware_month_end(year, month, local_zone)
        ioh_id=0#To avoid vue.js warnings
        
        plio=models.PlInvestmentOperations.from_all(dt_year_month, request.user.profile.currency, 1)
        for investment in plio.qs_investments():
            for ioh in plio.d_io_historical(investment.id):
                if ioh["dt_end"].year==year and ioh["dt_end"].month==month:
                    ioh["id"]=ioh_id
                    ioh["name"]=investment.fullName()
                    ioh["operationstypes"]=request.build_absolute_uri(reverse('operationstypes-detail', args=(ioh["operationstypes_id"],  )))
                    ioh["years"]=plio.ioh_years(ioh)
                    ioh["currency_user"]=request.user.profile.currency
                    list_ioh.append(ioh)
                    ioh_id=ioh_id+1
        list_ioh= sorted(list_ioh,  key=lambda item: item['dt_end'])
        return list_ioh
    ####
    r={}
    r["expenses"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.Expense,  request.user.profile.currency, request.user.profile.zone)
    r["incomes"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.Income,  request.user.profile.currency, request.user.profile.zone)
    r["dividends"]=dividends()
    r["fast_operations"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, eOperationType.FastOperations,  request.user.profile.currency, request.user.profile.zone)
    r["gains"]=listdict_investmentsoperationshistorical(request, year, month, request.user.profile.currency, request.user.profile.zone)
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportAnnualGainsByProductstypes(request, year):
#    gains=cursor_rows("""
#select 
#    investments.id, 
#    productstypes_id, 
#    (investment_operations(investments.id, make_timestamp(%s,12,31,23,59,59)::timestamp with time zone, %s, 'investmentsoperations')).io_historical 
#from  
#    investments, 
#    products 
#where investments.products_id=products.id""", (year, request.user.profile.currency, ))
    dt_from=dtaware_year_start(year, request.user.profile.zone)
    dt_to=dtaware_year_end(year, request.user.profile.zone)

    plio=models.PlInvestmentOperations.from_ids(dt_to, request.user.profile.currency, None, 1)
    
    #This inner joins its made to see all productstypes_id even if they are Null.
    # Subquery for dividends is used due to if I make a where from dividends table I didn't get null productstypes_id
    dividends=cursor_rows("""
select  
    productstypes_id, 
    sum(dividends.gross) as gross,
    sum(dividends.net) as net
from 
    products
    left join investments on products.id=investments.products_id
    left join (select * from dividends where extract('year' from datetime)=%s) dividends on investments.id=dividends.investments_id
group by productstypes_id""", (year, ))
    dividends_dict=lod.lod2dod(dividends, "productstypes_id")
    l=[]
    for pt in models.Productstypes.objects.all():
        gains_net=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user", pt.id)
        gains_gross=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_gross_user", pt.id)
#        gains_net, gains_gross= 0, 0
        dividends_gross, dividends_net=0, 0
#        for row in gains:
#            if row["productstypes_id"]==pt.id:
#                io_historical=eval(row["io_historical"])
#                for ioh in io_historical:
#                    if int(ioh["dt_end"][0:4])==year:
#                        gains_net=gains_net+ioh["gains_net_user"]
#                        gains_gross=gains_gross+ioh["gains_gross_user"]
        try:
            dividends_gross=dividends_dict[pt.id]["gross"]
        except:
            dividends_gross=0
        try:
            dividends_net=dividends_dict[pt.id]["net"]
        except:
            dividends_net=0

        l.append({
                "id": pt.id, 
                "name":pt.name, 
                "gains_gross": gains_gross, 
                "dividends_gross":dividends_gross, 
                "gains_net":gains_net, 
                "dividends_net": dividends_net, 
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
    return JsonResponse( l, encoder=MyDjangoJSONEncoder,     safe=False)



@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportConcepts(request):
    year=RequestGetInteger(request, "year")
    month=RequestGetInteger(request,  "month")
    if year is None or month is None:
        return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)
        
    r={}
    r["positive"]=[]
    month_balance_positive=0
    dict_month_positive={}
    r["negative"]=[]
    month_balance_negative=0
    dict_month_negative={}
    dict_median={}
    
    concepts=models.Concepts.objects.all().select_related("operationstypes")
    
    ## median
    for row in cursor_rows("""
        select
            concepts_id as id, 
            median(amount) as median
        from 
            accountsoperations
        group by 
            concepts_id
        """):
        dict_median[row['id']]=row['median']
    ## Data
    for row in cursor_rows("""
        select
            concepts_id as id, 
            sum(amount) as total
        from 
            accountsoperations,
            concepts
        where 
            date_part('year', datetime)=%s and
            date_part('month', datetime)=%s and
            concepts.operationstypes_id in (1,2) and
            accountsoperations.concepts_id=concepts.id
        group by 
            concepts_id
        """, (year, month)):
        if row['total']>=0:
            month_balance_positive+=row['total']
            dict_month_positive[row['id']]=row['total']
        else:
            month_balance_negative+=row['total']
            dict_month_negative[row['id']]=row['total']

    ## list
    for concept in concepts:
        if concept.id in dict_month_positive.keys():
            r["positive"].append({
                "concept": request.build_absolute_uri(reverse('concepts-detail', args=(concept.pk, ))), 
                "name": concept.name, 
                "operationstypes": request.build_absolute_uri(reverse('operationstypes-detail', args=(concept.pk, ))), 
                "total": dict_month_positive.get(concept.id, 0), 
                "percentage_total": Percentage(dict_month_positive.get(concept.id, 0), month_balance_positive), 
                "median":dict_median.get(concept.id, 0), 
            })   
    ## list negative
    for concept in concepts:
        if concept.id in dict_month_negative.keys():
            r["negative"].append({
                "concept": request.build_absolute_uri(reverse('concepts-detail', args=(concept.pk, ))), 
                "name": concept.name, 
                "operationstypes": request.build_absolute_uri(reverse('operationstypes-detail', args=(concept.pk, ))), 
                "total": dict_month_negative.get(concept.id, 0), 
                "percentage_total": Percentage(dict_month_negative.get(concept.id, 0), month_balance_negative), 
                "median":dict_median.get(concept.id, 0), 
            })

    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)




@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportDividends(request):
    qs_investments=models.Investments.objects.filter(active=True).select_related("products").select_related("accounts").select_related("products__leverages").select_related("products__productstypes")
    shares=cursor_rows_as_dict("investments_id", """
        select 
            investments.id as investments_id ,
            coalesce(sum(shares),0) as shares
            from investments left join investmentsoperations on investments.id=investmentsoperations.investments_id group by investments.id""")
    estimations=cursor_rows_as_dict("products_id",  """
        select 
            distinct(products.id) as products_id, 
            estimation, 
            date_estimation,
            (last_penultimate_lastyear(products.id, now())).last 
        from products, estimations_dps where products.id=estimations_dps.products_id and year=%s""", (date.today().year, ))
    quotes=cursor_rows_as_dict("products_id",  """
        select 
            products_id, 
            products.currency,
            (last_penultimate_lastyear(products.id, now())).last 
            from products, investments where investments.products_id=products.id and investments.active=true""")
    ld_report=[]
    for inv in qs_investments:        
        if shares[inv.id] is None: #Left join
            shares[inv.id]=0
        if inv.products_id in estimations:
            dps=estimations[inv.products_id]["estimation"]
            date_estimation=estimations[inv.products_id]["date_estimation"]
            percentage=Percentage(dps, quotes[inv.products_id]["last"])
            estimated=shares[inv.id]["shares"]*dps*inv.products.real_leveraged_multiplier()
        else:
            dps= None
            date_estimation=None
            percentage=Percentage()
            estimated=None
        
        
        d={
            "product": request.build_absolute_uri(reverse('products-detail', args=(inv.products.id, ))), 
            "name":  inv.fullName(), 
            "current_price": quotes[inv.products_id]["last"], 
            "dps": dps, 
            "shares": shares[inv.id]["shares"], 
            "date_estimation": date_estimation, 
            "estimated": estimated, 
            "percentage": percentage,  
            "currency": quotes[inv.products_id]["currency"]
        }
        ld_report.append(d)
    return JsonResponse( ld_report, encoder=MyDjangoJSONEncoder,     safe=False)



@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportEvolutionAssets(request, from_year):
    tb={}
    for year in range(from_year-1, date.today().year+1):
        tb[year]=models.Assets.pl_total_balance(dtaware_month_end(year, 12, request.user.profile.zone), request.user.profile.currency)
        
    d_incomes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Income), "year")
    d_expenses=lod.lod2dod(models.Assets.lod_ym_balance_user_by_operationstypes(request, eOperationType.Expense), "year")
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request), "year")

    # Dictionary can have missing years if there isn't data in database, so I must fill them
    for year in range(from_year, date.today().year+1):
        for dict_ in [d_incomes, d_expenses, d_dividends]:
            if not year in dict_:
                dict_[year]={"total":0}

    list_=[]
    for year in range(from_year, date.today().year+1): 
        dt_from=dtaware_year_start(year, request.user.profile.zone)
        dt_to=dtaware_year_end(year, request.user.profile.zone)
        plio=models.PlInvestmentOperations.from_all(dt_to, request.user.profile.currency, 1)
        dividends=d_dividends[year]["total"]
        incomes=d_incomes[year]["total"]-dividends
        expenses=d_expenses[year]["total"]
        gains=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user")
        list_.append({
            "year": year, 
            "balance_start": tb[year-1]["total_user"], 
            "balance_end": tb[year]["total_user"],  
            "diff": tb[year]["total_user"]-tb[year-1]["total_user"], 
            "incomes":incomes, 
            "gains_net": gains, 
            "dividends_net":dividends, 
            "expenses":expenses, 
            "total":incomes+gains+dividends+expenses, 
        })
    return JsonResponse( list_, encoder=MyDjangoJSONEncoder,     safe=False)
    
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])

def ReportEvolutionAssetsChart(request):
    def month_results(year, month,  local_currency, local_zone):
        dt=dtaware_month_end(year, month, local_zone)
        return dt, models.Assets.pl_total_balance(dt, local_currency)
    #####################
    year_from=RequestGetInteger(request, "from")
    if year_from==date.today().year:
        months_12=date.today()-timedelta(days=365)
        list_months=months(months_12.year, months_12.month)
    else:
        list_months=months(year_from, 1)
        
    l=[]
    futures=[]
    
    # HA MEJORADO UNOS 5 segundos de 10 segundos a 3 para 12 meses
    with ThreadPoolExecutor(max_workers=settings.CONCURRENCY_DB_CONNECTIONS_BY_USER) as executor:
        for year,  month in list_months:    
            futures.append(executor.submit(month_results, year, month, request.user.profile.currency,  request.user.profile.zone))

#    futures= sorted(futures, key=lambda future: future.result()[0])#month_end
    for future in futures:
        dt, total=future.result()
        l.append({
            "datetime":dt, 
            "total_user": total["total_user"], 
            "invested_user":total["investments_invested_user"], 
            "investments_user":total["investments_user"], 
            "accounts_user":total["accounts_user"], 
        })
    return JsonResponse( l, encoder=MyDjangoJSONEncoder,     safe=False)
    


@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionInvested(request, from_year):
    list_=[]
    qs=models.Investments.objects.all().select_related("products")
    d_dividends=lod.lod2dod(models.Dividends.lod_ym_netgains_dividends(request), "year")
    d_custody_commissions=lod.lod2dod(models.Assets.lod_ym_balance_user_by_concepts(request, [eConcept.CommissionCustody, ] ), "year")
    d_taxes=lod.lod2dod(models.Assets.lod_ym_balance_user_by_concepts(request, [eConcept.TaxesReturn, eConcept.TaxesPayment, ] ), "year")

    # Dictionary can have missing years if there isn't data in database, so I must fill them
    for year in range(from_year, date.today().year+1):
        for dict_ in [d_dividends, d_custody_commissions, d_taxes]:
            if not year in dict_:
                dict_[year]={"total":0}

    for year in range(from_year, date.today().year+1): 
        dt_from=dtaware_year_start(year, request.user.profile.zone)
        dt_to=dtaware_year_end(year, request.user.profile.zone)
        plio=models.PlInvestmentOperations.from_qs(dt_to, request.user.profile.currency, qs, 1)

        d={}
        d['year']=year
        d['invested']=plio.sum_total_io_current()["invested_user"]
        d['balance']=plio.sum_total_io_current()["balance_futures_user"]
        d['diff']=d['balance']-d['invested']
        d['percentage']=percentage_between(d['invested'], d['balance'])
        d['net_gains_plus_dividends']=plio.io_historical_sum_between_dt(dt_from, dt_to, "gains_net_user")+d_dividends[year]["total"]
        d['custody_commissions']=d_custody_commissions[year]["total"]
        d['taxes']=d_taxes[year]["total"] 
        d['investment_commissions']=plio.io_sum_between_dt(dt_from, dt_to, "commission_account")
        list_.append(d)
    
    return JsonResponse( list_, encoder=MyDjangoJSONEncoder, safe=False)







@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportsInvestmentsLastOperation(request):
    method=RequestGetInteger(request, "method", 0)
    ld=[]
    investments=models.Investments.objects.filter(active=True).select_related("accounts", "products")
    if method==0: #Separated investments
        plio=models.PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, investments, 1)
        
        investments_urls=[]
        for investment in plio.qs_investments():
            ioc_last=plio.io_current_last_operation_excluding_additions(investment.id)
            investments_urls.append(request.build_absolute_uri(reverse('investments-detail', args=(investment.pk, ))), )
        
            if ioc_last is None:
                continue
            ld.append({
                "id": investment.id, 
                "name": investment.fullName(), 
                "datetime": ioc_last["datetime"], 
                "last_shares": ioc_last['shares'], 
                "last_price": ioc_last['price_investment'], 
                "decimals": investment.products.decimals, 
                "shares": plio.d_total_io_current(investment.id)["shares"],  
                "balance": plio.d_total_io_current(investment.id)["balance_futures_user"],  
                "gains": plio.d_total_io_current(investment.id)["gains_gross_user"],  
                "percentage_last": plio.ioc_percentage_total_user(ioc_last), 
                "percentage_invested":  plio.total_io_current_percentage_total_user(investment.id).value, 
                "percentage_sellingpoint": plio.total_io_current_percentage_sellingpoint(investment.id, investment.selling_price).value,   
                "investments_urls": investments_urls, 
            })
    elif method==1:#Merginc current operations
        plio=models.PlInvestmentOperations.from_merging_io_current(timezone.now(), request.user.profile.currency, investments, 1)
        for virtual_investment_id in plio.list_investments_id():
            virtual_investment_product=models.Products.objects.get(pk=virtual_investment_id)
            
            ioc_last=plio.io_current_last_operation_excluding_additions(virtual_investment_id)
            investments_urls=[] #Investments merged in this virtual_investment
            for investment_id in plio.d_data(virtual_investment_id)["investments_id"]:
                investments_urls.append(request.build_absolute_uri(reverse('investments-detail', args=(investment_id, ))), )
            
            if ioc_last is None:
                continue
            ld.append({
                "id": virtual_investment_product.id, 
                "name": _("IOC merged investment of '{0}'").format( virtual_investment_product.fullName()), 
                "datetime": ioc_last["datetime"], 
                "last_shares": ioc_last['shares'], 
                "last_price": ioc_last['price_investment'], 
                "decimals": virtual_investment_product.decimals, 
                "shares": plio.d_total_io_current(virtual_investment_id)["shares"],  
                "balance": plio.d_total_io_current(virtual_investment_id)["balance_futures_user"],  
                "gains": plio.d_total_io_current(virtual_investment_id)["gains_gross_user"],  
                "percentage_last": plio.total_io_current_percentage_total_user(virtual_investment_id).value, 
                "percentage_invested": plio.ioc_percentage_total_user(ioc_last), 
                "percentage_sellingpoint": 0, # plio.percentage_sellingpoint(ioc_last, investment.selling_price).value,   
                "investments_urls": investments_urls, 
            })
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportCurrentInvestmentsOperations(request):
    ld=[]
    investments=models.Investments.objects.filter(active=True).select_related("accounts","products")
    plio=models.PlInvestmentOperations.from_qs(timezone.now(), request.user.profile.currency, investments, 1)
    
    for inv in plio.qs_investments():
        for o in plio.d_io_current(inv.id):
            o["name"]=inv.fullName()
            ld.append(o)
    ld=lod.lod_order_by(ld, "datetime")
    
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder, safe=False)

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportRanking(request):
    plio=models.PlInvestmentOperations.from_ids(timezone.now(), request.user.profile.currency, None, mode=2)

    ld=[]
    dividends=cursor_rows_as_dict("investments_id","select investments_id, sum(net) from dividends group by investments_id")
    for product in models.Products.objects.order_by().distinct("investments__products").select_related("stockmarkets"):
        d={}
        d["id"]=product.id
        d["name"]=product.fullName()
        d["current_net_gains"]=0
        d["historical_net_gains"]=0
        d["dividends"]=0
        d["investments"]=[]#List of all urls of investments
        for investments_id in plio.list_investments_id():
            if plio.d_data(investments_id)["products_id"]==product.id:
                d["investments"].append(request.build_absolute_uri(reverse('investments-detail', args=(investments_id, ))))
                d["current_net_gains"]=d["current_net_gains"]+plio.d_total_io_current(investments_id)["gains_net_user"]
                d["historical_net_gains"]=d["historical_net_gains"]+plio.d_total_io_historical(investments_id)["gains_net_user"]
                if int(investments_id) in dividends:
                    d["dividends"]=d["dividends"]+dividends[int(investments_id)]["sum"]
        d["total"]=Decimal(d["current_net_gains"])+Decimal(d["historical_net_gains"])+Decimal(d["dividends"])
        ld.append(d)
        
    ld=lod.lod_order_by(ld, "total", True)
    ranking=1
    for d in ld:
        d["ranking"]=ranking
        ranking=ranking+1
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)
    

@api_view(['GET', ])
@permission_classes([permissions.IsAuthenticated, ])
def Statistics(request):
    r=[]
    for name, cls in ((_("Accounts"), models.Accounts), (_("Accounts operations"), models.Accountsoperations), (_("Banks"), models.Banks), (_("Concept"),  models.Concepts)):
        r.append({"name": name, "value":cls.objects.all().count()})
    return JsonResponse(r, safe=False)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, ])
## Stores a filename encoded to base64 in /TMPFILE
## @param data     data:image/png;base64,ABVC
## @filename photo Without extension
def StoreFile(request):
    data=RequestString(request, "data")
    filename=RequestString(request, "filename")
    if all_args_are_not_none(data, filename):
        mime=data.split(";")[0].split(":")[1]
        extension=guess_extension(mime)
        content=data.split(",")[1]
        with open(f"{settings.TMPDIR}/{filename}{extension}", "wb") as f:
            f.write(b64decode(content))
        return JsonResponse(True, safe=False)  
    return JsonResponse(False, safe=False)  

class EstimationsDpsViewSet(viewsets.ModelViewSet):
    queryset = models.EstimationsDps.objects.all()
    serializer_class = serializers.EstimationsDpsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    def get_queryset(self):
        # To get active or inactive accounts
        product=RequestGetUrl(self.request, "product", models.Products)
        if product is not None:
            return self.queryset.filter(products=product)
        else:
            return self.queryset
    
class StockmarketsViewSet(CatalogModelViewSet):
    queryset = models.Stockmarkets.objects.all()
    serializer_class = serializers.StockmarketsSerializer

class FastOperationsCoverageViewSet(viewsets.ModelViewSet):
    queryset = models.FastOperationsCoverage.objects.all().select_related("investments__products")
    serializer_class = serializers.FastOperationsCoverageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        year=RequestGetInteger(self.request, 'year')
        month=RequestGetInteger(self.request, 'month')
        if all_args_are_not_none(year, month):
            return self.queryset.filter(datetime__year=year, datetime__month=month)
        return self.queryset
