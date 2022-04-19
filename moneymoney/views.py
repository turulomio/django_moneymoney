from base64 import  b64encode, b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from json import loads
from moneymoney.investmentsoperations import IOC, InvestmentsOperations,  InvestmentsOperationsManager, InvestmentsOperationsTotals, InvestmentsOperationsTotalsManager, StrategyIO
from moneymoney.reusing.connection_dj import execute, cursor_one_field, cursor_rows, cursor_one_column, cursor_rows_as_dict
from moneymoney.reusing.casts import string2list_of_integers
from moneymoney.reusing.datetime_functions import dtaware_month_start,  dtaware_month_end, dtaware_year_end, string2dtaware, dtaware_year_start, months, dtaware_day_end_from_date
from moneymoney.reusing.listdict_functions import listdict2dict, listdict_order_by, listdict_sum, listdict_median, listdict_average
from moneymoney.reusing.currency import Currency
from moneymoney.reusing.decorators import timeit
from moneymoney.reusing.percentage import Percentage,  percentage_between
from requests import delete, post
from moneymoney.request_casting import RequestBool, RequestDate, RequestDecimal, RequestDtaware, RequestUrl, RequestGetString, RequestGetUrl, RequestGetBool, RequestGetInteger, RequestGetArrayOfIntegers, RequestGetDtaware, RequestListOfIntegers, RequestInteger, RequestGetListOfIntegers, RequestString, RequestListUrl, id_from_url, all_args_are_not_none
from urllib import request as urllib_request

from moneymoney.models import (
    Banks, 
    Accounts, 
    Accountsoperations, 
    Comment, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Dividends,
    Investments, 
    Investmentsoperations, 
    Leverages, 
    Operationstypes, 
    Orders, 
    Products, 
    Productspairs, 
    Productstypes, 
    Quotes, 
    Stockmarkets, 
    Strategies, 
    currencies_in_accounts, 
    percentage_to_selling_point, 
    total_balance, 
    balance_user_by_operationstypes, 
    eComment, 
    eConcept, 
    eOperationType, 
    RANGE_RECOMENDATION_CHOICES, 
)
from moneymoney import serializers
from os import path, system
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from django.core.serializers.json import DjangoJSONEncoder
from zoneinfo import available_timezones
from tempfile import TemporaryDirectory

class MyDjangoJSONEncoder(DjangoJSONEncoder):    
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, Percentage):
            return o.value
        if isinstance(o, Currency):
            return o.amount
        return super().default(o)

@api_view(['POST'])
def login(request):
    try:
        user=User.objects.get(username=request.POST.get("username"))
    except User.DoesNotExist:
        return Response("Invalid user")
        
    password=request.POST.get("password")
    pwd_valid=check_password(password, user.password)
    if not pwd_valid:
        return Response("Wrong password")

    if Token.objects.filter(user=user).exists():#Lo borra
        token=Token.objects.get(user=user)
        token.delete()
    token=Token.objects.create(user=user)
    return Response(token.key)
    
@api_view(['POST'])
def logout(request):
    token=Token.objects.get(key=request.POST.get("key"))
    if token is None:
        return Response("Invalid token")
    else:
        token.delete()
        return Response("Logged out")


@csrf_exempt
@permission_classes([permissions.IsAuthenticated, ])
def CatalogManager(request):
    r=False
    print(request.user.get_all_permissions())
    if request.user.has_perm('catalog_manager'):
        r=True
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)


@csrf_exempt
@api_view(['GET', ])    
def AssetsReport(request):
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


@csrf_exempt
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def ConceptsMigration(request):         
    concept_from=RequestUrl(request, "from", Concepts)
    concept_to=RequestUrl(request, "to", Concepts)
    if concept_from is not None and concept_to is not None:
        execute("update accountsoperations set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
        execute("update creditcardsoperations set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
        execute("update dividends set concepts_id=%s where concepts_id=%s", (concept_to.id, concept_from.id))
        return Response({'status': 'details'}, status=status.HTTP_200_OK)
    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ConceptsUsed(request): 
    qs=Concepts.objects.all() 
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



@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def CreditcardsPayments(request): 
    creditcard=RequestGetUrl(request, "creditcard", Creditcards)
    
    if creditcard is not None:
    
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
    else:
        return Response({'status': 'Credit card not found'}, status=status.HTTP_400_BAD_REQUEST)

    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

class ConceptsViewSet(viewsets.ModelViewSet):
    queryset = Concepts.objects.all()
    serializer_class = serializers.ConceptsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    

class CreditcardsViewSet(viewsets.ModelViewSet):
    queryset = Creditcards.objects.all()
    serializer_class = serializers.CreditcardsSerializer
    permission_classes = [permissions.IsAuthenticated]      
    
    def get_queryset(self):
        active=RequestGetBool(self.request, 'active')
        account_id=RequestGetInteger(self.request, 'account')

        if account_id is not None and active is not None:
            return self.queryset.filter(accounts_id=account_id,  active=active)
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset.all()


class CreditcardsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Creditcardsoperations.objects.all().select_related("creditcards").select_related("creditcards__accounts")
    serializer_class = serializers.CreditcardsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
        
    def get_queryset(self):
        ##Saca los pagos hechos en esta operación de cuenta
        accountsoperations_id=RequestGetInteger(self.request, 'accountsoperations_id')
        if accountsoperations_id is not None:
            return self.queryset.filter(accountsoperations__id=accountsoperations_id)
        else:
            return self.queryset.all()

class DividendsViewSet(viewsets.ModelViewSet):
    queryset = Dividends.objects.all()
    serializer_class = serializers.DividendsSerializer
    permission_classes = [permissions.IsAuthenticated] 
    
    
    ## To use this methos use axios 
    ##            var headers={...this.myheaders(),params:{investments: [1,2,3],otra:"OTTRA"}}
    ##            return axios.get(`${this.$store.state.apiroot}/api/dividends/`, headers)
    def get_queryset(self):
        investments_ids=RequestGetArrayOfIntegers(self.request,"investments[]") 
        datetime=RequestGetDtaware(self.request, 'from')
        if len(investments_ids)>0 and datetime is None:
            return self.queryset.filter(investments__in=investments_ids).order_by("datetime")
        elif len(investments_ids)>0 and datetime is not None:
            return self.queryset.filter(investments__in=investments_ids,  datetime__gte=datetime).order_by("datetime")
        else:
            return self.queryset.order_by("datetime")
    
class OrdersViewSet(viewsets.ModelViewSet):
    queryset = Orders.objects.all()
    serializer_class = serializers.OrdersSerializer
    permission_classes = [permissions.IsAuthenticated]  

class OperationstypesViewSet(viewsets.ModelViewSet):
    queryset = Operationstypes.objects.all()
    serializer_class = serializers.OperationstypesSerializer
    permission_classes = [permissions.IsAuthenticated]  

class StrategiesViewSet(viewsets.ModelViewSet):
    queryset = Strategies.objects.all()
    serializer_class = serializers.StrategiesSerializer
    permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        active=RequestGetBool(self.request, "active")
        investment=RequestGetUrl(self.request, "investment", Investments)
        type=RequestGetInteger(self.request, "type")
        if all_args_are_not_none(active, investment):
            return self.queryset.filter(dt_to__isnull=active,  investments__contains=investment.id, type=type)
        return self.queryset.all() #We need to rerun all(), because it cached results after CRUD operations

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def StrategiesWithBalance(request):        
    active=RequestGetBool(request, 'active')
    if active is None:
        qs=Strategies.objects.all() 
    else:
        if active is True:
            qs=Strategies.objects.filter(dt_to__isnull=True)
        else:
            qs=Strategies.objects.filter(dt_to__isnull=False)

    r=[]
    for strategy in qs:
        dividends_net_user=0
        s=StrategyIO(request, strategy)
        gains_current_net_user=s.current_gains_net_user() 
        gains_historical_net_user=s.historical_gains_net_user()
        dividends_net_user=Dividends.net_gains_baduser_between_datetimes_for_some_investments(strategy.investments_ids(), strategy.dt_from, strategy.dt_to_for_comparations())
        r.append({
            "id": strategy.id,  
            "url": request.build_absolute_uri(reverse('strategies-detail', args=(strategy.pk, ))), 
            "name":strategy.name, 
            "dt_from": strategy.dt_from, 
            "dt_to": strategy.dt_to, 
            "invested": s.current_invested_user(), 
            "gains_current_net_user":  gains_current_net_user,  
            "gains_historical_net_user": gains_historical_net_user, 
            "dividends_net_user": dividends_net_user, 
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


@csrf_exempt
@api_view(['GET', ])    
def home(request):
    return JsonResponse( True,  encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsClasses(request):
    qs_investments_active=Investments.objects.filter(active=True).select_related("products").select_related("products__productstypes").select_related("accounts").select_related("products__leverages")
    iotm=InvestmentsOperationsTotalsManager.from_investment_queryset(qs_investments_active, timezone.now(), request)
    return JsonResponse( iotm.json_classes(), encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
@api_view(['GET', ])
@permission_classes([permissions.IsAuthenticated, ])
def Time(request):
    return JsonResponse( timezone.now(), encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@api_view(['GET', ])    
def Timezones(request):
    r=list(available_timezones())
    r.sort()
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = Investments.objects.select_related("accounts").all()
    serializer_class = serializers.InvestmentsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_queryset(self):
        # To get active or inactive accounts
        active=RequestGetBool(self.request, "active")
        bank_id=RequestGetInteger(self.request,"bank")

        if bank_id is None and active is None:
            return self.queryset.all()
        elif bank_id is not None:
            return self.queryset.filter(accounts__banks__id=bank_id,  active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset.all()


class InvestmentsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Investmentsoperations.objects.select_related("investments").select_related("investments__products").all()
    serializer_class = serializers.InvestmentsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.investments.set_attributes_after_investmentsoperations_crud()
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
    
@csrf_exempt
@api_view(['POST', 'PUT', 'DELETE' ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def AccountTransfer(request): 
    account_origin=RequestUrl(request, 'account_origin', Accounts)#Returns an account object
    account_destiny=RequestUrl(request, 'account_destiny', Accounts)
    datetime=RequestDtaware(request, 'datetime')
    amount=RequestDecimal(request, 'amount')
    commission=RequestDecimal(request, 'commission',  0)
    ao_origin=RequestUrl(request, 'ao_origin', Accountsoperations)
    ao_destiny=RequestUrl(request, 'ao_destiny', Accountsoperations)
    ao_commission=RequestUrl(request, 'ao_commission', Accountsoperations)
    if request.method=="POST":
        if ( account_destiny is not None and account_origin is not None and datetime is not None and amount is not None and amount >=0 and commission is not None and commission >=0 and account_destiny!=account_origin):
            if commission >0:
                ao_commission=Accountsoperations()
                ao_commission.datetime=datetime
                concept_commision=Concepts.objects.get(pk=eConcept.BankCommissions)
                ao_commission.concepts=concept_commision
                ao_commission.operationstypes=concept_commision.operationstypes
                ao_commission.amount=-commission
                ao_commission.accounts=account_origin
                ao_commission.save()

            #Origin
            ao_origin=Accountsoperations()
            ao_origin.datetime=datetime
            concept_transfer_origin=Concepts.objects.get(pk=eConcept.TransferOrigin)
            ao_origin.concepts=concept_transfer_origin
            ao_origin.operationstypes=concept_transfer_origin.operationstypes
            ao_origin.amount=-amount
            ao_origin.accounts=account_origin
            ao_origin.save()
            print(ao_origin)

            #Destiny
            ao_destiny=Accountsoperations()
            ao_destiny.datetime=datetime
            concept_transfer_destiny=Concepts.objects.get(pk=eConcept.TransferDestiny)
            ao_destiny.concepts=concept_transfer_destiny
            ao_destiny.operationstypes=concept_transfer_destiny.operationstypes
            ao_destiny.amount=amount
            ao_destiny.accounts=account_destiny
            ao_destiny.save()

            #Encoding comments
            ao_origin.comment=Comment().encode(eComment.AccountTransferOrigin, ao_origin, ao_destiny, ao_commission)
            ao_origin.save()
            ao_destiny.comment=Comment().encode(eComment.AccountTransferDestiny, ao_origin, ao_destiny, ao_commission)
            ao_destiny.save()
            if ao_commission is not None:
                ao_commission.comment=Comment().encode(eComment.AccountTransferOriginCommission, ao_origin, ao_destiny, ao_commission)
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
    queryset = Accounts.objects.select_related("banks").all()
    serializer_class = serializers.AccountsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_queryset(self):
        active=RequestGetBool(self.request, 'active')
        bank_id=RequestGetInteger(self.request, 'bank')

        if bank_id is not None:
            return self.queryset.filter(banks__id=bank_id,   active=True)
            
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset.all()

class AccountsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Accountsoperations.objects.all()
    serializer_class = serializers.AccountsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    def get_queryset(self):
        search=RequestGetString(self.request, 'search')

        if search is not None:
            return self.queryset.filter(comment__icontains=search)
        else:
            return self.queryset.all()
            
class BanksViewSet(viewsets.ModelViewSet):
    queryset = Banks.objects.all()
    permission_classes = [permissions.IsAuthenticated]  
    serializer_class =  serializers.BanksSerializer

    def get_queryset(self):
        active=RequestGetBool(self.request, "active")
        if active is not None:
            return self.queryset.filter(active=active)
        return self.queryset.all() #We need to rerun all(), because it cached results after CRUD operations

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def BanksWithBalance(request):
    active=RequestGetBool(request, 'active')
    if active is None:
        qs=Banks.objects.all() 
    else:
        qs=Banks.objects.filter(active=active)
            
    r=[]
    for o in qs:
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
        
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def AccountsWithBalance(request):
    active=RequestGetBool(request, 'active')
    bank_id=RequestGetInteger(request, 'bank')

    if bank_id is not None:
        qs=Accounts.objects.select_related("banks").filter(banks__id=bank_id,   active=True)
    elif active is not None:
        qs=Accounts.objects.select_related("banks").filter( active=active)
    else:
        qs=Accounts.objects.select_related("banks").all()
            
    r=[]
    for o in qs:
        balance_account, balance_user=o.balance(timezone.now(), request.local_currency ) 
        r.append({
            "id": o.id,  
            "name": o.name, 
            "active":o.active, 
            "url":request.build_absolute_uri(reverse('accounts-detail', args=(o.pk, ))), 
            "number": o.number, 
            "balance_account": balance_account,  
            "balance_user": balance_user, 
            "is_deletable": o.is_deletable(), 
            "currency": o.currency, 
            "banks":request.build_absolute_uri(reverse('banks-detail', args=(o.banks.pk, ))), 
            "localname": _(o.name), 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def AccountsoperationsWithBalance(request):        
    accounts_id=RequestGetInteger(request, 'account')
    year=RequestGetInteger(request, 'year')
    month=RequestGetInteger(request, 'month')
    
    
    if all_args_are_not_none(accounts_id, year, month):
        account=Accounts.objects.get(pk=accounts_id)
        dt_initial=dtaware_month_start(year, month, request.local_zone)
        initial_balance=account.balance( dt_initial, request.local_currency)[0]
        qs=Accountsoperations.objects.select_related("accounts").select_related("operationstypes").select_related("concepts").filter(datetime__year=year, datetime__month=month, accounts__id=accounts_id).order_by("datetime")

    r=[]
    for o in qs:
        r.append({
            "id": o.id,  
            "url": request.build_absolute_uri(reverse('accountsoperations-detail', args=(o.pk, ))), 
            "datetime":o.datetime, 
            "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(o.concepts.pk, ))), 
            "operationstypes":request.build_absolute_uri(reverse('operationstypes-detail', args=(o.operationstypes.pk, ))), 
            "amount": o.amount, 
            "balance":  initial_balance + o.amount, 
            "comment": o.comment, 
            "comment_decoded": Comment().decode(o.comment), 
            "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.pk, ))), 
            "currency": o.accounts.currency, 
            "is_editable": o.is_editable(), 
        })
        initial_balance=initial_balance + o.amount
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def CreditcardsoperationsPayments(request, pk):
    creditcard=Creditcards.objects.get(pk=pk)
    dt_payment=RequestDtaware(request, "dt_payment")
    cco_ids=RequestListOfIntegers(request, "cco")
    
    if creditcard is not None and dt_payment is not None and cco_ids is not None:
        qs_cco=Creditcardsoperations.objects.all().filter(pk__in=(cco_ids))
        sumamount=0
        for o in qs_cco:
            sumamount=sumamount+o.amount
        
        c=Accountsoperations()
        c.datetime=dt_payment
        c.concepts=Concepts.objects.get(pk=eConcept.CreditCardBilling)
        c.operationstypes=c.concepts.operationstypes
        c.amount=sumamount
        c.accounts=creditcard.accounts
        c.comment="Transaction in progress"
        c.save()
        c.comment=Comment().encode(eComment.CreditCardBilling, creditcard, c)
        c.save()

        #Modifica el registro y lo pone como paid y la datetime de pago y añade la opercuenta
        for o in qs_cco:
            o.paid_datetime=dt_payment
            o.paid=True
            o.accountsoperations_id=c.id
            o.save()
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
    return JsonResponse( False, encoder=MyDjangoJSONEncoder,     safe=False)
    

@csrf_exempt
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def CreditcardsoperationsPaymentsRefund(request):
    
    accountsoperations_id=RequestInteger(request, 'accountsoperations_id')
    if accountsoperations_id is not None:
        ao=Accountsoperations.objects.get(pk=accountsoperations_id)
    
    if ao is not None:
        Creditcardsoperations.objects.filter(accountsoperations_id=ao.id).update(paid_datetime=None,  paid=False, accountsoperations_id=None)
        ao.delete() #Must be at the end due to middle queries

        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
    return JsonResponse( False, encoder=MyDjangoJSONEncoder,     safe=False)
    
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def CreditcardsoperationsWithBalance(request):        
    creditcard_id=RequestGetInteger(request, 'creditcard')
    paid=RequestGetBool(request, 'paid')
    if creditcard_id is not None and paid is not None:
        initial_balance=0
        qs=Creditcardsoperations.objects.select_related("creditcards").select_related("operationstypes").select_related("concepts").filter(paid=paid, creditcards__id=creditcard_id).order_by("datetime")

    r=[]
    for o in qs:
        r.append({
            "id": o.id,  
            "url": request.build_absolute_uri(reverse('creditcardsoperations-detail', args=(o.pk, ))), 
            "datetime":o.datetime, 
            "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(o.concepts.pk, ))), 
            "operationstypes":request.build_absolute_uri(reverse('operationstypes-detail', args=(o.operationstypes.pk, ))), 
            "amount": o.amount, 
            "balance":  initial_balance + o.amount, 
            "comment": Comment().decode(o.comment), 
            "creditcards":request.build_absolute_uri(reverse('creditcards-detail', args=(o.creditcards.pk, ))), 
            "paid": o.paid, 
            "paid_datetime": o.paid_datetime, 
            "currency": o.creditcards.accounts.currency, 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def CreditcardsWithBalance(request):        
    accounts_id=RequestGetInteger(request, 'account')
    active=RequestGetBool(request, 'active')
    
    if accounts_id is not None and active is not None:
        qs=Creditcards.objects.select_related("accounts").filter(accounts__id=accounts_id, active=active).order_by("name")
    else:
        qs=Creditcards.objects.select_related("accounts").order_by("name")

    r=[]
    for o in qs:
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



@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsWithBalance(request):

    active=RequestGetBool(request, 'active', None)
    bank_id=RequestGetInteger(request, 'bank', None)

    if bank_id is not None:
        qs=Investments.objects.select_related("accounts").select_related("products").select_related("products__productstypes").select_related("products__leverages").filter(accounts__banks__id=bank_id,   active=True)
    elif active is not None:
        qs=Investments.objects.select_related("accounts").select_related("products").select_related("products__productstypes").select_related("products__leverages").filter( active=active)
    else:
        qs=Investments.objects.select_related("accounts").select_related("products").select_related("products__productstypes").select_related("products__leverages").all()
            
    r=[]
    for o in qs:
        iot=InvestmentsOperationsTotals.from_investment(request, o, timezone.now(), request.local_currency)
        percentage_invested=None if iot.io_total_current["invested_user"]==0 else  iot.io_total_current["gains_gross_user"]/iot.io_total_current["invested_user"]

        r.append({
            "id": o.id,  
            "name":o.name, 
            "fullname":o.fullName(), 
            "active":o.active, 
            "url":request.build_absolute_uri(reverse('investments-detail', args=(o.pk, ))), 
            "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.id, ))), 
            "product": request.build_absolute_uri(reverse('products-detail', args=(o.products.id, ))), 
            "products":request.build_absolute_uri(reverse('products-detail', args=(o.products.id, ))), 
            "last_datetime": o.products.basic_results()['last_datetime'], 
            "last": o.products.basic_results()['last'], 
            "daily_difference": iot.current_last_day_diff(), 
            "daily_percentage":percentage_between(o.products.basic_results()['penultimate'], o.products.basic_results()['last']), 
            "invested_user": iot.io_total_current["invested_user"], 
            "gains_user": iot.io_total_current["gains_gross_user"], 
            "balance_user": iot.io_total_current["balance_user"], 
            "currency": o.products.currency, 
            "currency_account": o.accounts.currency, 
            "percentage_invested": percentage_invested, 
            "percentage_selling_point": percentage_to_selling_point(iot.io_total_current["shares"], iot.investment.selling_price, iot.investment.products.basic_results()['last']), 
            "selling_expiration": o.selling_expiration, 
            "shares":iot.io_total_current["shares"], 
            "balance_percentage": o.balance_percentage, 
            "daily_adjustment": o.daily_adjustment, 
            "selling_price": o.selling_price, 
            "is_deletable": o.is_deletable(), 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)




@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFull(request):
    ids=RequestGetListOfIntegers(request, "investments")
    r=[]
    for o in Investments.objects.filter(id__in=ids):
        r.append(InvestmentsOperations.from_investment(request, o, timezone.now(), request.local_currency).json())
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@api_view(['POST', ]) 
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFullSimulation(request):
    investments=[]
    for url in request.data["investments"]:
        investments.append(RequestUrl(request, url, Investments))## Como todas deben ser iguales uso la primera
    dt=string2dtaware(request.data["dt"],  "JsUtcIso", request.local_zone)
    local_currency=request.data["local_currency"]
    temporaltable=request.data["temporaltable"]
    listdict=request.data["operations"]
    for d in listdict:
        d["datetime"]=string2dtaware(d["datetime"],  "JsUtcIso", request.local_zone)
        d["investments_id"]=investments[0].id
        d["operationstypes_id"]=id_from_url(request, d["operationstypes"])
    r=InvestmentsOperations.from_investment_simulation(request, investments,  dt,  local_currency,  listdict,  temporaltable).json()
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@api_view(['GET', ]) 
@permission_classes([permissions.IsAuthenticated, ])
def StrategiesSimulation(request):
    strategy=RequestGetUrl(request, "strategy", Strategies)
    dt=RequestGetDtaware(request, "dt")
    temporaltable=RequestGetString(request, "temporaltable")
    simulated_operations=[]
    if strategy is not None:
        s=StrategyIO(request, strategy, dt, simulated_operations, temporaltable)
        return JsonResponse( s.json(), encoder=MyDjangoJSONEncoder,  safe=False)
    return Response({'status': _('Strategy was not found')}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsEvolutionChart(request):
    id=RequestGetInteger(request, "investment")
    io=InvestmentsOperations.from_investment(request, Investments.objects.get(pk=id), timezone.now(), request.local_currency)
    return JsonResponse( io.chart_evolution(), encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@transaction.atomic
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsChangeSellingPrice(request):
    selling_price=RequestDecimal(request, "selling_price")
    selling_expiration=RequestDate(request, "selling_expiration")
    investments=RequestListUrl(request, "investments", Investments)
    
    if investments is not None and selling_price is not None: #Pricce 
        for inv in investments:
            inv.selling_price=selling_price
            inv.selling_expiration=selling_expiration
            inv.save()
        return JsonResponse( True, encoder=MyDjangoJSONEncoder,     safe=False)
    return Response({'status': 'Investment or selling_price is None'}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
@transaction.atomic

@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsOperationsTotalManager_investments_same_product(request):
    product=RequestGetUrl(request, "product", Products)
    if product is not None:
        qs_investments=Investments.objects.filter(products=product, active=True)
        iotm=InvestmentsOperationsTotalsManager.from_investment_queryset(qs_investments,  timezone.now(), request)
        return JsonResponse( iotm.json(), encoder=MyDjangoJSONEncoder,     safe=False)
    return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)

class LeveragesViewSet(viewsets.ModelViewSet):
    queryset = Leverages.objects.all()
    serializer_class = serializers.LeveragesSerializer
    permission_classes = [permissions.IsAuthenticated]  


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def OrdersList(request):        
    active=RequestGetBool(request, 'active')
    expired=RequestGetBool(request, 'expired')
    executed=RequestGetBool(request, 'executed')
    if active is not None:
        qs=Orders.objects.filter(expiration__gte=date.today(),  executed__isnull=True).select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__productstypes").select_related("investments__products__leverages")
    elif expired is not None:
        qs=Orders.objects.filter(expiration__lte=date.today(),  executed__isnull=True).select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__productstypes").select_related("investments__products__leverages")
    elif executed is not None:
        qs=Orders.objects.filter(executed__isnull=False).select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__productstypes").select_related("investments__products__leverages")
    else:
        qs=Orders.objects.all().select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__productstypes").select_related("investments__products__leverages")

    r=[]
    for o in qs:
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
    
 
@csrf_exempt
@transaction.atomic
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsFavorites(request):
    product=RequestUrl(request, "product", Products)
    favorites=getGlobalListOfIntegers(request, "favorites")
    if product is not None:
        if product.id in favorites:
            favorites.remove(product.id)
        else:
            favorites.append(product.id)
        setGlobal("favorites", str(favorites)[1:-1])
    return JsonResponse( favorites, encoder=MyDjangoJSONEncoder,     safe=False)

 
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsInformation(request):
    first_year=RequestGetInteger(request, "first_year",  2005)
    product=RequestGetUrl(request, "product", Products)
    
    if product is None:
        return Response({'status': "Product wan't found"}, status=status.HTTP_404_NOT_FOUND)
    
     #Calculo 1 mes antes
    rows_month=cursor_rows("""
WITH quotes as (
	SELECT 
		dates::date - interval '1 day' date, 
		(select quote from quote(%s, dates - interval '1 day')), 
		lag((select quote from quote(%s, dates - interval '1 day')),1) over(order by dates::date) 
	from 
		generate_series('%s-01-01'::date - interval '1 day','%s-01-01'::date, '1 month') dates
)
select date,lag, quote, percentage(lag,quote)  from quotes;
""", (product.id, product.id, first_year, date.today().year+1))
    rows_month.pop(0)
    
    #Calculo 1 año antes
    rows_year=cursor_rows("""
WITH quotes as (
	SELECT 
		dates::date - interval '1 day' date, 
		(select quote from quote(%s, dates - interval '1 day')), 
		lag((select quote from quote(%s, dates - interval '1 day')),1) over(order by dates::date) 
	from 
		generate_series('%s-01-01'::date - interval '1 day','%s-01-02'::date, '1 year') dates
)
select date, lag, quote, percentage(lag,quote)  from quotes;
""", (product.id, product.id, first_year, date.today().year+1))
    rows_year.pop(0)
#    ld_print(rows_month)
#    ld_print(rows_year)
    #PERCENTAGES
    ld_percentage=[]
    d={ 'm1': 0, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0, 'm6': 0, 'm7': 0, 'm8': 0, 'm9': 0, 'm10': 0, 'm11': 0, 'm12': 0}
    for i in range(0, len(rows_month)):
        month=(i % 12 )+1
        d[f"m{month}"]=Percentage(rows_month[i]["percentage"], 100)
        if month==12:
            ld_percentage.append(d)
            d={ 'm1': 0, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0, 'm6': 0, 'm7': 0, 'm8': 0, 'm9': 0, 'm10': 0, 'm11': 0, 'm12': 0}

    if month!=12:
        ld_percentage.append(d)

    for i in range(0, len(rows_year)):
        ld_percentage[i]["year"]=first_year+i 
        ld_percentage[i]['m13']=Percentage(rows_year[i]["percentage"], 100) 
        
    #QUOTES
    ld_quotes=[]
    d={ 'm1': 0, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0, 'm6': 0, 'm7': 0, 'm8': 0, 'm9': 0, 'm10': 0, 'm11': 0, 'm12': 0}
    for i in range(0, len(rows_month)):
        month=(i % 12 )+1
        d[f"m{month}"]=rows_month[i]["quote"]
        if month==12:
            ld_quotes.append(d)
            d={ 'm1': 0, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0, 'm6': 0, 'm7': 0, 'm8': 0, 'm9': 0, 'm10': 0, 'm11': 0, 'm12': 0}
    if month!=12:
        ld_quotes.append(d)

    for i in range(0, len(rows_year)):
        ld_quotes[i]["year"]=first_year+i 

    r={"quotes":ld_quotes, "percentages":ld_percentage}
    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsPairs(request):
    #fromyear=RequestGetInteger(request, "fromyear", date.today().year-3) 
    product_better=RequestGetUrl(request, "a", Products)
    product_worse=RequestGetUrl(request, "b", Products)
    
    if product_better.currency==product_worse.currency:
        common_quotes=cursor_rows("""
            select 
                make_date(a.year, a.month,1) as date, 
                a.products_id as a, 
                a.open as a_open, 
                b.products_id as b, 
                b.open as b_open 
            from 
                ohclmonthlybeforesplits(%s) as a ,
                ohclmonthlybeforesplits(%s) as b 
            where 
                a.year=b.year and 
                a.month=b.month
        UNION ALL
            select
                now()::date as date,
                %s as a, 
                (select last from last_penultimate_lastyear(%s,now())) as a_open, 
                %s as b, 
                (select last from last_penultimate_lastyear(%s,now())) as b_open
                """, (product_worse.id, product_better.id, 
                product_worse.id, product_worse.id, product_better.id, product_better.id))
    else: #Uses worse currency
        #Fist condition in where it's to remove quotes without money_convert due to no data
        common_quotes=cursor_rows("""
            select 
                make_date(a.year,a.month,1) as date, 
                a.products_id as a, 
                a.open as a_open, 
                b.products_id as b, 
                money_convert(make_date(a.year,a.month,1)::timestamp with time zone, b.open, %s, %s) as b_open
            from 
                ohclmonthlybeforesplits(%s) as a 
                ,ohclmonthlybeforesplits(%s) as b 
            where 
                b.open != money_convert(make_date(a.year,a.month,1)::timestamp with time zone, b.open, %s, %s)  and
                a.year=b.year and 
                a.month=b.month
        UNION ALL
            select
                now()::date as date,
                %s as a, 
                (select last from last_penultimate_lastyear(%s,now())) as a_open, 
                %s as b, 
                money_convert(now(), (select last from last_penultimate_lastyear(%s,now())), %s,%s) as b_open
                """, ( product_better.currency,  product_worse.currency, 
                        product_worse.id, 
                        product_better.id, 
                        product_better.currency,  product_worse.currency, 
                        
                        product_worse.id,
                        product_worse.id,
                        product_better.id, 
                        product_better.id, product_better.currency,  product_worse.currency))
#def listdict_products_pairs_evolution_from_datetime(product_worse, product_better, common_quotes, basic_results_worse,   basic_results_better):

    r={}
    r["product_a"]={"name":product_better.fullName(), "currency": product_better.currency, "url": request.build_absolute_uri(reverse('products-detail', args=(product_better.id, )))}
    r["product_b"]={"name":product_worse.fullName(), "currency": product_worse.currency, "url": request.build_absolute_uri(reverse('products-detail', args=(product_worse.id, )))}
    r["data"]=[]
    last_pr=Percentage(0, 1)
    first_pr=common_quotes[0]["b_open"]/common_quotes[0]["a_open"]
    for row in common_quotes:#a worse, b better
        pr=row["b_open"]/row["a_open"]
        r["data"].append({
            "datetime": dtaware_day_end_from_date(row["date"], request.local_zone), 
            "price_worse": row["a_open"], 
            "price_better": row["b_open"], 
            "price_ratio": pr, 
            "price_ratio_percentage_from_start": percentage_between(first_pr, pr), 
            "price_ratio_percentage_month_diff": percentage_between(last_pr, pr), 
        })
        last_pr=pr
    
    #list_products_evolution=listdict_products_pairs_evolution_from_datetime(product_worse, product_better, common_monthly_quotes, basic_results_worse,  basic_results_better)

    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@api_view(['GET', 'DELETE' ])    
@permission_classes([permissions.IsAuthenticated, ])
## GET METHODS
## products/quotes/ohcl/?product_url To get all ohcls of a product
## products/quotes/ohcl/?product_url&year=2022&month=4 To get ochls of a product, in a month
## DELETE METHODS
## products/quotes/ohcl?product=url&date=2022-4-1
def ProductsQuotesOHCL(request):
    if request.method=="GET":
        product=RequestGetUrl(request, "product", Products)
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
        product=RequestUrl(request, "product", Products)
        date=RequestDate(request, "date")
        if product is not None and date is not None:
            qs=Quotes.objects.filter(products=product, datetime__date=date)
            qs.delete()
            return JsonResponse(True, encoder=MyDjangoJSONEncoder, safe=False)

    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsRanges(request):
    product=RequestGetUrl(request, "product", Products)
    only_first=RequestGetBool(request, "only_first")
    percentage_between_ranges=RequestGetInteger(request, "percentage_between_ranges")

    if percentage_between_ranges is not None:
        percentage_between_ranges=percentage_between_ranges/1000
    percentage_gains=RequestGetInteger(request, "percentage_gains")
    if percentage_gains is not None:
        percentage_gains=percentage_gains/1000
    amount_to_invest=RequestGetInteger(request, "amount_to_invest")
    recomendation_methods=RequestGetInteger(request, "recomendation_methods")
    investments_ids=RequestGetArrayOfIntegers(request,"investments[]") 
    if len(investments_ids)>0:
        qs_investments=Investments.objects.filter(id__in=investments_ids)
    else:
        qs_investments=Investments.objects.none()

    if all_args_are_not_none(product, only_first,  percentage_between_ranges, percentage_gains, amount_to_invest, recomendation_methods):
        from moneymoney.productrange import ProductRangeManager
        
        prm=ProductRangeManager(request, product, percentage_between_ranges, percentage_gains, only_first,  qs_investments=qs_investments, decimals=product.decimals)
        prm.setInvestRecomendation(recomendation_methods)

        return JsonResponse( prm.json(), encoder=MyDjangoJSONEncoder, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)
    
    
class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all().select_related("productstypes").select_related("leverages").select_related("stockmarkets")
    serializer_class = serializers.ProductsSerializer
    permission_classes = [permissions.IsAuthenticated]  

class ProductspairsViewSet(viewsets.ModelViewSet):
    queryset = Productspairs.objects.all()
    serializer_class = serializers.ProductspairsSerializer
    permission_classes = [permissions.IsAuthenticated]  

class ProductstypesViewSet(viewsets.ModelViewSet):
    queryset = Productstypes.objects.all()
    serializer_class = serializers.ProductstypesSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
@csrf_exempt
@api_view(['POST', ])
@permission_classes([permissions.IsAuthenticated, ])
def ProductsUpdate(request):
    from moneymoney.investing_com import InvestingCom
    auto=RequestBool(request, "auto", False) ## Uses automatic request with settings globals investing.com   
    if auto is True:
        with TemporaryDirectory() as tmp:
            system(f"""wget --header="Host: es.investing.com" \
    --header="User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0" \
    --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
    --header="Accept-Language: es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3" \
    --header="Accept-Encoding: gzip, deflate, br" \
    --header="Alt-Used: es.investing.com" \
    --header="Connection: keep-alive" \
    --referer="{request.globals.get('investing_com_referer', '')}" \
    --header="{request.globals.get('investing_com_cookie', '')}" \
    --header="Upgrade-Insecure-Requests: 1" \
    --header="Sec-Fetch-Dest: document" \
    --header="Sec-Fetch-Mode: navigate" \
    --header="Sec-Fetch-Site: same-origin" \
    --header="Sec-Fetch-User: ?1" \
    --header="Pragma: no-cache" \
    --header="Cache-Control: no-cache" \
    --header="TE: trailers" \
    "{request.globals.get('investing_com_url', '')}" -O {tmp}/portfolio.csv""")
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
            print()
            return Response({'status': "Uploaded file is too big ({} MB).".format(csv_file.size/(1000*1000),)}, status=status.HTTP_404_NOT_FOUND)

        ic=InvestingCom(request, product=None)
        ic.load_from_filename_in_memory(csv_file)
    r=ic.get()
    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
     
@csrf_exempt
@api_view(['POST', ])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def ProductsCatalogUpdate(request):
    ## If key desn't exist return None, if d["key"] is "" return None
    def checks_and_sets_value(d, key):
        if key not in d:
            return None
        if d[key]=="":
            return None
        return d[key]
    
    auto=RequestBool(request, "auto", False) ## Uses automatic request with settings globals investing.com   
    if auto is True:
        response = urllib_request. urlopen("https://raw.githubusercontent.com/turulomio/django_moneymoney/main/moneymoney/data/products.json")
        data =  loads(response. read())
    else:
        # if not GET, then proceed
        if "json_file1" not in request.FILES:
            return Response({'status': 'You must upload a file'}, status=status.HTTP_404_NOT_FOUND)
        else:
            json_file = request.FILES["json_file1"]
            
        if not json_file.name.endswith('.json'):
            return Response({'status': 'File has not .json extension'}, status=status.HTTP_404_NOT_FOUND)

        data=loads(json_file.read())


    r={}
    r["total"]=len(data["rows"])
    r["logs"]=[]
    for d in data["rows"]:
        p=Products()
        p.pk=d["id"]
        p.name=checks_and_sets_value(d, "name")
        p.isin=checks_and_sets_value(d, "isin")
        p.currency=checks_and_sets_value(d, "currency")
        p.productstypes=Productstypes.objects.get(pk=d["productstypes_id"])
        p.agrupations=checks_and_sets_value(d, "agrupations")
        p.web=checks_and_sets_value(d, "web")
        p.address=checks_and_sets_value(d, "address")
        p.phone=checks_and_sets_value(d, "phone")
        p.mail=checks_and_sets_value(d, "mail")
        p.percentage=checks_and_sets_value(d, "percentage")
        p.pci=checks_and_sets_value(d, "pci")
        p.leverages=Leverages.objects.get(pk=d["leverages_id"])
        p.stockmarkets=Stockmarkets.objects.get(pk=d["stockmarkets_id"])
        p.comment=checks_and_sets_value(d, "comment")
        p.obsolete=checks_and_sets_value(d, "obsolete")
        p.ticker_yahoo=checks_and_sets_value(d, "ticker_yahoo")
        p.ticker_morningstar=checks_and_sets_value(d, "ticker_morningstar")
        p.ticker_google=checks_and_sets_value(d, "ticker_google")
        p.ticker_quefondos=checks_and_sets_value(d, "ticker_quefondos")
        p.ticker_investingcom=checks_and_sets_value(d, "ticker_investingcom")
        p.decimals=checks_and_sets_value(d, "decimals")
        before=Products.objects.get(pk=d["id"])
        
        if before is None:
            r["logs"].append({"product":str(p), "log":_("Created")})
        elif not p.is_fully_equal(before):
            r["logs"].append({"product":str(p), "log":_("Updated")})
        p.save()
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)
 
class QuotesViewSet(viewsets.ModelViewSet):
    queryset = Quotes.objects.all().select_related("products")
    serializer_class = serializers.QuotesSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    ## api/quotes/ Show all quotes of the database
    ## api/quotes/?future=true Show all quotes with datetime in the future for debugging
    ## api/quotes/?last=true Shows all products last Quotes
    ## api/quotes/?product=url Showss all quotes of a product
    ## api/quotes/?product=url&month=1&year=2021 Showss all quotes of a product in a month
    def get_queryset(self):
        product=RequestGetUrl(self.request, 'product', Products)
        future=RequestGetBool(self.request, 'future')
        last=RequestGetBool(self.request, 'last')
        month=RequestGetInteger(self.request, 'month')
        year=RequestGetInteger(self.request, 'year')
        
        if future is True:
            return Quotes.objects.all().filter(datetime__gte=timezone.now()).select_related("products").order_by("datetime")
                
        ## Search last quote of al linvestments
        if last is True:
            qs=Quotes.objects.raw("""
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

        if product is not None and year is not None and month is not None:
            return Quotes.objects.all().filter(products=product, datetime__year=year, datetime__month=month).select_related("products").order_by("datetime")
        if product is not None:
            return Quotes.objects.all().filter(products=product).select_related("products").order_by("datetime")
            
        return self.queryset

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def RecomendationMethods(request): 
    r=[]
    for id, name in RANGE_RECOMENDATION_CHOICES:
        r.append({
            "id":id, 
            "name":name, 
            "localname": _(name), 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnual(request, year):
    def month_results(month_end, month_name, local_currency):
        return month_end, month_name, total_balance(month_end, local_currency)
        
    #####################
    local_zone=request.local_zone
    local_currency=request.local_currency
    dtaware_last_year=dtaware_year_end(year-1, local_zone)
    last_year_balance=total_balance(dtaware_last_year, request.local_currency)['total_user']
    list_=[]
    futures=[]
    
    # HA MEJORADO UNOS 5 segundos de 7 a 2
    with ThreadPoolExecutor(max_workers=settings.CONCURRENCY_DB_CONNECTIONS_BY_USER) as executor:
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
        
            month_end=dtaware_month_end(year, month, local_zone)
            futures.append(executor.submit(month_results, month_end,  month_name, local_currency))

    futures= sorted(futures, key=lambda future: future.result()[0])#month_end
    last_month=last_year_balance
    for future in futures:
        month_end, month_name,  total = future.result()
        list_.append({
            "month_number":month_end, 
            "month": month_name,
            "account_balance":total['accounts_user'], 
            "investment_balance":total['investments_user'], 
            "total":total['total_user'] , 
            "percentage_year": percentage_between(last_year_balance, total['total_user'] ), 
            "diff_lastmonth": total['total_user']-last_month, 
        })
        last_month=total['total_user']
        
    r={"last_year_balance": last_year_balance,  "dtaware_last_year": dtaware_last_year,  "data": list_}
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
 
 

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncome(request, year):   
    def month_results(year,  month, month_name):
        dividends=Dividends.netgains_dividends(year, month)
        incomes=balance_user_by_operationstypes(year,  month,  eOperationType.Income, local_currency, local_zone)-dividends
        expenses=balance_user_by_operationstypes(year,  month,  eOperationType.Expense, local_currency, local_zone)
        
        
        dt_from=dtaware_month_start(year, month,  request.local_zone)
        dt_to=dtaware_month_end(year, month,  request.local_zone)
        gains=iom.historical_gains_net_user_between_dt(dt_from, dt_to)
        total=incomes+gains+expenses+dividends
        return month_name, month,  year,  incomes, expenses, gains, dividends, total
    
    list_=[]
    futures=[]
    local_zone=request.local_zone
    local_currency=request.local_currency
    #IOManager de final de año para luego calcular gains entre fechas
    dt_year_to=dtaware_year_end(year, request.local_zone)
    iom=InvestmentsOperationsManager.from_investment_queryset(Investments.objects.all(), dt_year_to, request)

    
    # HA MEJORADO UNOS 3 segundos de 16 a 13
    with ThreadPoolExecutor(max_workers=settings.CONCURRENCY_DB_CONNECTIONS_BY_USER) as executor:
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
            futures.append(executor.submit(month_results, year, month, month_name))
        
        for future in as_completed(futures):
            month_name, month,  year,  incomes, expenses, gains, dividends, total = future.result()
            list_.append({
                "id": f"{year}/{month}/", 
                "month_number":month, 
                "month": month_name,
                "incomes":incomes, 
                "expenses":expenses, 
                "gains":gains, 
                "dividends":dividends, 
                "total":total,  
            })
            
    list_= sorted(list_, key=lambda item: item["month_number"])
    return JsonResponse( list_, encoder=MyDjangoJSONEncoder,     safe=False)
    

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncomeDetails(request, year, month):
    def listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, operationstypes_id, local_currency, local_zone):
        # Expenses
        r=[]
        balance=0
        for currency in currencies_in_accounts():
            for op in cursor_rows("""
                select datetime,concepts_id, amount, comment, accounts.id as accounts_id
                from 
                    accountsoperations,
                    accounts
                where 
                    operationstypes_id=%s and 
                    date_part('year',datetime)=%s and
                    date_part('month',datetime)=%s and
                    accounts.currency=%s and
                    accounts.id=accountsoperations.accounts_id   
            union all 
                select datetime,concepts_id, amount, comment, accounts.id as accounts_id
                from 
                    creditcardsoperations ,
                    creditcards,
                    accounts
                where 
                    operationstypes_id=%s and 
                    date_part('year',datetime)=%s and
                    date_part('month',datetime)=%s and
                    accounts.currency=%s and
                    accounts.id=creditcards.accounts_id and
                    creditcards.id=creditcardsoperations.creditcards_id""", (operationstypes_id, year, month,  currency, operationstypes_id, year, month,  currency)):
                if local_currency==currency:
                    balance=balance+op["amount"]
                    r.append({
                        "id":-1, 
                        "datetime": op['datetime'], 
                        "concepts":request.build_absolute_uri(reverse('concepts-detail', args=(op["concepts_id"], ))), 
                        "amount":op['amount'], 
                        "balance": balance,
                        "comment_decoded":Comment().decode(op["comment"]), 
                        "currency": currency, 
                        "account": request.build_absolute_uri(reverse('accounts-detail', args=(op["accounts_id"], ))), 
                    })
                else:
                    print("TODO")
                
            r= sorted(r,  key=lambda item: item['datetime'])
    #            r=r+money_convert(dtaware_month_end(year, month, local_zone), balance, currency, local_currency)
        return r
    def dividends():
        r=[]
        for o in Dividends.objects.all().filter(datetime__year=year, datetime__month=month).order_by('datetime'):
            r.append({"id":o.id, "datetime":o.datetime, "concepts":o.concepts.name, "gross":o.gross, "net":o.net, "taxes":o.taxes, "commission":o.commission})
        return r
    def listdict_investmentsoperationshistorical(request, year, month, local_currency, local_zone):
        #Git investments with investmentsoperations in this year, month
        list_ioh=[]
        dt_year_month=dtaware_month_end(year, month, local_zone)
        ioh_id=0#To avoid vue.js warnings
        for investment in Investments.objects.raw("select distinct(investments.*) from investmentsoperations, investments where date_part('year', datetime)=%s and date_part('month', datetime)=%s and investments.id=investmentsoperations.investments_id", (year, month)):
            investments_operations=InvestmentsOperations.from_investment(request, investment, dt_year_month, local_currency)
            
            for ioh in investments_operations.io_historical:
                if ioh['dt_end'].year==year and ioh['dt_end'].month==month:
                    ioh["id"]=ioh_id
                    ioh["name"]=investment.fullName()
                    ioh["operationstypes"]=request.build_absolute_uri(reverse('operationstypes-detail', args=(ioh["operationstypes_id"],  )))
                    ioh["years"]=round(Decimal((ioh["dt_end"]-ioh["dt_start"]).days/365), 2)
                    list_ioh.append(ioh)
                    ioh_id=ioh_id+1
        list_ioh= sorted(list_ioh,  key=lambda item: item['dt_end'])
        return list_ioh
    ####
    r={}
    r["expenses"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, 1,  request.local_currency, request.local_zone)
    r["incomes"]=listdict_accountsoperations_creditcardsoperations_by_operationstypes_and_month(year, month, 2,  request.local_currency, request.local_zone)
    r["dividends"]=dividends()
    r["gains"]=listdict_investmentsoperationshistorical(request, year, month, request.local_currency, request.local_zone)

    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualGainsByProductstypes(request, year):
    local_currency=request.local_currency
    gains=cursor_rows("""
select 
    investments.id, 
    productstypes_id, 
    (investment_operations(investments.id, make_timestamp(%s,12,31,23,59,59)::timestamp with time zone, %s, 'investmentsoperations')).io_historical 
from  
    investments, 
    products 
where investments.products_id=products.id""", (year, local_currency, ))
    
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
    dividends_dict=listdict2dict(dividends, "productstypes_id")
    l=[]
    for pt in Productstypes.objects.all():
        gains_net, gains_gross= 0, 0
        dividends_gross, dividends_net=0, 0
        for row in gains:
            if row["productstypes_id"]==pt.id:
                io_historical=eval(row["io_historical"])
                for ioh in io_historical:
                    if int(ioh["dt_end"][0:4])==year:
                        gains_net=gains_net+ioh["gains_net_user"]
                        gains_gross=gains_gross+ioh["gains_gross_user"]
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
    return JsonResponse( l, encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
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
    
    concepts=Concepts.objects.all().select_related("operationstypes")
    
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
    accountsoperations
where 
    date_part('year', datetime)=%s and
    date_part('month', datetime)=%s and
    operationstypes_id in (1,2)
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


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportConceptsHistorical(request):
    concept=RequestGetUrl(request, "concept", Concepts)
    if concept is None:
        return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)
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
    r["total"]=listdict_sum(json_concepts_historical, "total")
    r["median"]=listdict_median(rows, 'value')
    r["average"]=listdict_average(rows, 'value')
    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportDividends(request):
    qs_investments=Investments.objects.filter(active=True).select_related("products").select_related("accounts").select_related("products__leverages").select_related("products__productstypes")
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


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionAssets(request, from_year):
    tb={}
    for year in range(from_year-1, date.today().year+1):
        tb[year]=total_balance(dtaware_month_end(year, 12, request.local_zone), request.local_currency)
    
    
    list_=[]
    for year in range(from_year, date.today().year+1): 
        dt_from=dtaware_year_start(year, request.local_zone)
        dt_to=dtaware_year_end(year, request.local_zone)
        
        iom=InvestmentsOperationsManager.from_investment_queryset(Investments.objects.all(), dt_to, request)
        dividends=Dividends.net_gains_baduser_between_datetimes(dt_from, dt_to)
        incomes=balance_user_by_operationstypes(year, None,  eOperationType.Income, request.local_currency, request.local_zone)-dividends
        expenses=balance_user_by_operationstypes(year, None,  eOperationType.Expense, request.local_currency, request.local_zone)
        gains=iom.historical_gains_net_user_between_dt(dt_from, dt_to)
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
    
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionAssetsChart(request):
    def month_results(year, month,  local_currency, local_zone):
        dt=dtaware_month_end(year, month, local_zone)
        return dt, total_balance(dt, local_currency)
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
            futures.append(executor.submit(month_results, year, month, request.local_currency,  request.local_zone))

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
    

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionInvested(request, from_year):
    list_=[]
    qs=Investments.objects.all()
    for year in range(from_year, date.today().year+1): 
        iom=InvestmentsOperationsManager.from_investment_queryset(qs, dtaware_month_end(year, 12, request.local_zone), request)
        dt_from=dtaware_year_start(year, request.local_zone)
        dt_to=dtaware_year_end(year, request.local_zone)
        
        custody_commissions=cursor_one_field("select sum(amount) from accountsoperations where concepts_id = %s and datetime>%s and datetime<= %s", (eConcept.CommissionCustody, dt_from, dt_to))
        taxes=cursor_one_field("select sum(amount) from accountsoperations where concepts_id in( %s,%s) and datetime>%s and datetime<= %s", (eConcept.TaxesReturn, eConcept.TaxesPayment, dt_from, dt_to))
        d={}
        d['year']=year
        d['invested']=iom.current_invested_user()
        d['balance']=iom.current_balance_futures_user()
        d['diff']=d['balance']-d['invested']
        d['percentage']=percentage_between(d['invested'], d['balance'])
        d['net_gains_plus_dividends']=iom.historical_gains_net_user_between_dt(dt_from, dt_to)+Dividends.net_gains_baduser_between_datetimes_for_some_investments(iom.list_of_investments_ids(), dt_from, dt_to)
        d['custody_commissions']=0 if custody_commissions is None else custody_commissions
        d['taxes']=0 if taxes is None else taxes
        d['investment_commissions']=iom.o_commissions_account_between_dt(dt_from, dt_to)
        list_.append(d)
    return JsonResponse( list_, encoder=MyDjangoJSONEncoder,     safe=False)






@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportsInvestmentsLastOperation(request):
    method=RequestGetInteger(request, "method", 0)
    ld=[]
    if method==0:
        investments=Investments.objects.filter(active=True).select_related("accounts").select_related("products")
        iom=InvestmentsOperationsManager.from_investment_queryset(investments, timezone.now(), request)
    elif method==1:#Merginc current operations
        iom=InvestmentsOperationsManager.merging_all_current_operations_of_active_investments(request, timezone.now())
        
    for io in iom:
        last=io.current_last_operation_excluding_additions()
        investments_urls=[]
        if method==0:
                investments_urls.append(request.build_absolute_uri(reverse('investments-detail', args=(io.investment.pk, ))), )
        if method==1:
            investments_same_product=Investments.objects.filter(active=True, products=io.investment.products).select_related("accounts").select_related("products")
            for inv in investments_same_product:
                investments_urls.append(request.build_absolute_uri(reverse('investments-detail', args=(inv.pk, ))), )
            
        if last is None:
            continue
        ioc_last=IOC(io.investment, last )
        ld.append({
            "id": io.investment.id, 
            "name": io.investment.fullName(), 
            "datetime": ioc_last.d["datetime"], 
            "last_shares": ioc_last.d['shares'], 
            "last_price": ioc_last.d['price_investment'], 
            "decimals": io.investment.products.decimals, 
            "shares": io.current_shares(),  
            "balance": io.current_balance_futures_user(),  
            "gains": io.current_gains_gross_user(),  
            "percentage_last": ioc_last.percentage_total_investment().value, 
            "percentage_invested": io.current_percentage_invested_user().value, 
            "percentage_sellingpoint": ioc_last.percentage_sellingpoint().value,   
            "investments_urls": investments_urls, 
        })
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)
    
    

@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportCurrentInvestmentsOperations(request):
    ld=[]
    investments=Investments.objects.filter(active=True).select_related("accounts").select_related("products")
    iom=InvestmentsOperationsManager.from_investment_queryset(investments, timezone.now(), request)
    
    for io in iom:
        for o in io.io_current:
            ioc=IOC(io.investment, o )
            ld.append({
                "id": io.investment.id, 
                "name": io.investment.fullName(), 
                "operationstypes":ioc.d["operationstypes"], 
                "datetime": ioc.d["datetime"], 
                "shares": ioc.d['shares'], 
                "price_user": ioc.d['price_user'], 
                "invested_user": ioc.d['invested_user'], 
                "balance_user": ioc.d["balance_user"], 
                "gains_gross_user": ioc.d['gains_gross_user'], 
                "percentage_annual_user": ioc.percentage_annual_user().value, 
                "percentage_apr_user": ioc.percentage_apr_user().value, 
                "percentage_total_user": ioc.percentage_total_user().value,   
            })
    ld=listdict_order_by(ld, "datetime")
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportRanking(request):
    iotm=InvestmentsOperationsTotalsManager.from_all_investments(request, timezone.now())
    products_ids=cursor_one_column('select distinct(products_id) from investments')
    products=Products.objects.all().filter(id__in=products_ids)
    ld=[]
    dividends=cursor_rows_as_dict("investments_id","select investments_id, sum(net) from dividends group by investments_id")
    for product in products:
        d={}
        d["id"]=product.id
        d["name"]=product.fullName()
        d["current_net_gains"]=0
        d["historical_net_gains"]=0
        d["dividends"]=0
        for iot in iotm.list:
            if iot.investment.products.id==product.id:
                d["current_net_gains"]=d["current_net_gains"]+iot.io_total_current["gains_net_user"]
                d["historical_net_gains"]=d["historical_net_gains"]+iot.io_total_historical["gains_net_user"]
                try:
                    d["dividends"]=d["dividends"]+dividends[iot.investment.id]["sum"]
                except:
                    pass
        d["total"]=d["current_net_gains"]+d["historical_net_gains"]+d["dividends"]
        ld.append(d)
        
    ld=listdict_order_by(ld, "total", True)
    ranking=1
    for d in ld:
        d["ranking"]=ranking
        ranking=ranking+1
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)
    
@csrf_exempt
@api_view(['GET', ])
@permission_classes([permissions.IsAuthenticated, ])
def Statistics(request):
    r=[]
    for name, cls in ((_("Accounts"), Accounts), (_("Accounts operations"), Accountsoperations), (_("Banks"), Banks), (_("Concept"),  Concepts)):
        r.append({"name": name, "value":cls.objects.all().count()})
    return JsonResponse(r, safe=False)

@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def Settings(request):
    if request.method == 'GET':
        r={}
        r['local_zone']=request.local_zone
        r['local_currency']=request.local_currency
        r['investing_com_referer']=request.globals.get("investing_com_referer", "")
        r['investing_com_cookie']=request.globals.get("investing_com_cookie", "")
        r['investing_com_url']=request.globals.get("investing_com_url", "")
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    elif request.method == 'POST':
        #Personal settings
        local_currency=RequestString(request,"local_currency")
        local_zone=RequestString(request,"local_zone")
        if local_currency is not None and local_zone is not None:
            setGlobal("mem/localcurrency", local_currency)
            setGlobal("mem/localzone", local_zone)
            
        # Investing.com
        investing_com_referer=RequestString(request, "investing_com_referer")
        investing_com_cookie=RequestString(request, "investing_com_cookie")
        investing_com_url=RequestString(request, "investing_com_url")
        if investing_com_referer is not None and investing_com_cookie is not None and investing_com_url is not None:
            setGlobal("investing_com_url", investing_com_url)
            setGlobal("investing_com_cookie", investing_com_cookie)
            setGlobal("investing_com_referer", investing_com_referer)
        return JsonResponse(True, safe=False)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, ])
## Stores a filename encoded to base64 in a global variable
## Global: base64_{name}.{extension}
## @param only binary data, don't have to include data:image/png;base64 or similar
## Para guardarlo a ficheros se puede hacer
##    f=open(f"/tmp/{filename}", "wb")
##    f.write(b64decode(data))
##    f.close()
### @global_ For Example: base64_assetsreport_report_annual_chart.png
def Binary2Global(request):
    data=RequestString(request, "data")
    global_=RequestString(request, "global")
    if data is not None  and global_ is not None:
        setGlobal(global_, data)
    return JsonResponse(True, safe=False)  

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def EstimationsDps_add(request):
    year=RequestInteger(request, 'year')
    estimation=RequestDecimal(request, 'estimation')
    product=RequestUrl(request, 'product', Products)
    if year is not None and estimation is not None  and product is not None:
        execute("delete from estimations_dps where products_id=%s and year=%s", (product.id, year))
        execute("insert into estimations_dps (date_estimation,year,estimation,source,manual,products_id) values(%s,%s,%s,%s,%s,%s)", (
            date.today(), year, estimation, "Internet", True, product.id))
        return JsonResponse(True, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)
    

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def EstimationsDps_delete(request):
    year=RequestInteger(request, 'year')
    product=RequestUrl(request, 'product', Products)
    if year is not None and product is not None:
        execute("delete from estimations_dps where products_id=%s and year=%s", (product.id, year))
        return JsonResponse(True, safe=False)
    return Response({'status': "EstimationDPS wasn't deleted"}, status=status.HTTP_404_NOT_FOUND)
    
@csrf_exempt
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def EstimationsDps_list(request): 
    product=RequestGetUrl(request, "product", Products)
    if product is not None:
        rows=cursor_rows("select * from estimations_dps where products_id=%s order by year", (product.id, ))

        for row in rows:
            row["product"]=request.build_absolute_uri(reverse('products-detail', args=(row["products_id"], )))
        return JsonResponse(rows, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)

class StockmarketsViewSet(viewsets.ModelViewSet):
    queryset = Stockmarkets.objects.all()
    serializer_class = serializers.StockmarketsSerializer
    permission_classes = [permissions.IsAuthenticated]  


def setGlobal(key, value):
    number=cursor_one_field("select count(*) from globals where global=%s", (key, ))
    if number==0:
        execute("insert into globals (global, value) values (%s,%s)", (key, value))
    else:
        execute("update globals set value=%s where global=%s", (value,  key))
    

## @param type Type to cast str, int, float,...
def getGlobalBytes_from_base64(request, key, default=None):
    try:
        return b64decode(request.globals.get(key, default))
    except:
        return default
    
    
def getGlobalListOfIntegers(request, key, default=[], separator=","):    
    try:
        r = string2list_of_integers(request.globals.GET.get(key), separator)
    except:
        r=default
    return r
