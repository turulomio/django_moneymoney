import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse, resolve
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.http import JsonResponse, HttpResponse
from moneymoney.investmentsoperations import IOC, InvestmentsOperations_from_investment,  InvestmentsOperationsManager_from_investment_queryset, InvestmentsOperationsTotals_from_investment, InvestmentsOperationsTotalsManager_from_all_investments, InvestmentsOperationsTotalsManager_from_investment_queryset, Simulate_InvestmentsOperations_from_investment
from moneymoney.reusing.connection_dj import execute, cursor_one_field, cursor_rows, cursor_one_column, cursor_rows_as_dict
from moneymoney.reusing.casts import str2bool, string2list_of_integers
from moneymoney.reusing.datetime_functions import dtaware_month_start,  dtaware_month_end, dtaware_year_end, string2dtaware, dtaware_year_start, months, dtaware_day_end_from_date
from moneymoney.reusing.listdict_functions import listdict2dict, listdict_order_by, listdict_sum, listdict_median, listdict_average
from moneymoney.reusing.decorators import timeit
from moneymoney.reusing.currency import Currency
from moneymoney.reusing.percentage import Percentage,  percentage_between

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
)
from moneymoney import serializers
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from django.core.serializers.json import DjangoJSONEncoder

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

@timeit
@csrf_exempt
@api_view(['GET', ])    
def AssetsReport(request):
    from moneymoney.assetsreport import generate_assets_report
    from base64 import b64encode
    filename=generate_assets_report(request)
    with open(filename, "rb") as pdf:
        encoded_string = b64encode(pdf.read())
        print(encoded_string[:100])
        return HttpResponse(encoded_string)

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
            return self.queryset


class CreditcardsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Creditcardsoperations.objects.all()
    serializer_class = serializers.CreditcardsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  

class DividendsViewSet(viewsets.ModelViewSet):
    queryset = Dividends.objects.all()
    serializer_class = serializers.DividendsSerializer
    permission_classes = [permissions.IsAuthenticated] 
    
    def get_queryset(self):
        investments_ids=RequestGetListOfIntegers(self.request, 'investments')
        datetime=RequestGetDtaware(self.request, 'from')
        print(investments_ids,  datetime)
        if investments_ids is not None and datetime is None:
            return self.queryset.filter(investments__in=investments_ids).order_by("datetime")
        elif investments_ids is not None and datetime is not None:
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
    for o in qs:
        gains_current_net_user=0
        gains_historical_net_user=0
        dividends_net_user=0
        
        investments_ids=string2list_of_integers(o.investments)
        qs_investments_in_strategy=Investments.objects.filter(id__in=(investments_ids))
        io_in_strategy=InvestmentsOperationsManager_from_investment_queryset(qs_investments_in_strategy, timezone.now(), request)
        
        gains_current_net_user=io_in_strategy.current_gains_net_user() 
        gains_historical_net_user=io_in_strategy.historical_gains_net_user_between_dt(o.dt_from, o.dt_to_for_comparations())
        dividends_net_user=Dividends.net_gains_baduser_between_datetimes_for_some_investments(investments_ids, o.dt_from, o.dt_to_for_comparations())
        r.append({
            "id": o.id,  
            "url": request.build_absolute_uri(reverse('strategies-detail', args=(o.pk, ))), 
            "name":o.name, 
            "dt_from": o.dt_from, 
            "dt_to": o.dt_to, 
            "invested": io_in_strategy.current_invested_user(), 
            "gains_current_net_user":  gains_current_net_user,  
            "gains_historical_net_user": gains_historical_net_user, 
            "dividends_net_user": dividends_net_user, 
            "total_net_user":gains_current_net_user + gains_historical_net_user + dividends_net_user, 
            "investments":o.investments, 
            "type": o.type, 
            "comment": o.comment, 
            "additional1": o.additional1, 
            "additional2": o.additional2, 
            "additional3": o.additional3, 
            "additional4": o.additional4, 
            "additional5": o.additional5, 
            "additional6": o.additional6, 
            "additional7": o.additional7, 
            "additional8": o.additional8, 
            "additional9": o.additional9, 
            "additional10": o.additional10, 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

#class EstimationsDpsViewSet(viewsets.ModelViewSet):
#    queryset = EstimationsDps.objects.all()
#    serializer_class = serializers.EstimationsDpsSerializer
#    permission_classes = [permissions.IsAuthenticated]  

@timeit
@csrf_exempt
@api_view(['GET', ])    
def home(request):
    return JsonResponse( True,  encoder=MyDjangoJSONEncoder,     safe=False)

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsClasses(request):
    qs_investments_active=Investments.objects.filter(active=True).select_related("products").select_related("products__productstypes").select_related("accounts").select_related("products__leverages")
    iotm=InvestmentsOperationsTotalsManager_from_investment_queryset(qs_investments_active, timezone.now(), request)
    return JsonResponse( iotm.json_classes(), encoder=MyDjangoJSONEncoder,     safe=False)

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def Timezones(request):
    from pytz import all_timezones
    return JsonResponse( all_timezones, encoder=MyDjangoJSONEncoder,     safe=False)

class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = Investments.objects.select_related("accounts").all()
    serializer_class = serializers.InvestmentsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_queryset(self):
        # To get active or inactive accounts
        active=RequestGetBool(self.request, "active")
        bank_id=RequestGetInteger(self.request,"bank")

        if bank_id is None and active is None:
            return self.queryset
        elif bank_id is not None:
            return self.queryset.filter(accounts__banks__id=bank_id,  active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset


class InvestmentsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Investmentsoperations.objects.all()
    serializer_class = serializers.InvestmentsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
@csrf_exempt
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def AccountTransfer(request): 
    origin=RequestPostUrl(request, 'origin')#Returns an account object
    destiny=RequestPostUrl(request, 'destiny')
    datetime=RequestPostDtaware(request, 'datetime')
    amount=RequestPostDecimal(request, 'amount')
    commission=RequestPostDecimal(request, 'commission',  0)
    print(origin, destiny, datetime, amount,  commission)
    if (
        destiny is not None and
        origin is not None and
        datetime is not None and
        amount is not None and amount >=0 and
        commission >=0 and
        destiny.id!=origin.id
    ):
        if commission >0:
            ao_commission=Accountsoperations()
            ao_commission.datetime=datetime
            concept_commision=Concepts.objects.get(pk=eConcept.BankCommissions)
            ao_commission.concepts=concept_commision
            ao_commission.operationstypes=concept_commision.operationstypes
            ao_commission.amount=-commission
            ao_commission.accounts=origin
            ao_commission.save()
        else:
            ao_commission=None

        #Origin
        ao_origin=Accountsoperations()
        ao_origin.datetime=datetime
        concept_transfer_origin=Concepts.objects.get(pk=eConcept.TransferOrigin)
        ao_origin.concepts=concept_transfer_origin
        ao_origin.operationstypes=concept_transfer_origin.operationstypes
        ao_origin.amount=-amount
        ao_origin.accounts=origin
        ao_origin.save()

        #Destiny
        ao_destiny=Accountsoperations()
        ao_destiny.datetime=datetime
        concept_transfer_destiny=Concepts.objects.get(pk=eConcept.TransferDestiny)
        ao_destiny.concepts=concept_transfer_destiny
        ao_destiny.operationstypes=concept_transfer_destiny.operationstypes
        ao_destiny.amount=amount
        ao_destiny.accounts=destiny
        ao_destiny.save()

        #Encoding comments
        ao_origin.comment=Comment().encode(eComment.AccountTransferOrigin, ao_origin, ao_destiny, ao_commission)
        ao_origin.save()
        ao_destiny.comment=Comment().encode(eComment.AccountTransferDestiny, ao_origin, ao_destiny, ao_commission)
        ao_destiny.save()
        if ao_commission is not None:
            ao_commission.comment=Comment().encode(eComment.AccountTransferOriginCommission, ao_origin, ao_destiny, ao_commission)
            ao_commission.save()
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
            return self.queryset

class AccountsoperationsViewSet(viewsets.ModelViewSet):
    queryset = Accountsoperations.objects.all()
    serializer_class = serializers.AccountsoperationsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    def get_queryset(self):
        search=RequestGetString(self.request, 'search')

        if search is not None:
            return self.queryset.filter(comment__icontains=search)
        else:
            return self.queryset
            
class BanksViewSet(viewsets.ModelViewSet):
    queryset = Banks.objects.all()
    permission_classes = [permissions.IsAuthenticated]  
    serializer_class =  serializers.BanksSerializer

    def get_queryset(self):
        try:
            active = str2bool(self.request.GET.get('active'))
        except:
            active=None
        if active is None:
            return self.queryset
        else:
            return self.queryset.filter(active=active)


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
            "name":o.name, 
            "active":o.active, 
            "url":request.build_absolute_uri(reverse('banks-detail', args=(o.pk, ))), 
            "balance_accounts": balance_accounts, 
            "balance_investments": balance_investments, 
            "balance_total": balance_accounts+balance_investments, 
            "is_deletable": o.is_deletable()
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
            "name":o.name, 
            "active":o.active, 
            "url":request.build_absolute_uri(reverse('accounts-detail', args=(o.pk, ))), 
            "number": o.number, 
            "balance_account": balance_account,  
            "balance_user": balance_user, 
            "is_deletable": o.is_deletable(), 
            "currency": o.currency, 
            "banks__name": o.banks.name,  
            "banks":request.build_absolute_uri(reverse('banks-detail', args=(o.banks.pk, ))), 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)


@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def AccountsoperationsWithBalance(request):        
    accounts_id=RequestGetInteger(request, 'account')
    year=RequestGetInteger(request, 'year')
    month=RequestGetInteger(request, 'month')
    
    
    if accounts_id is not None and year is not None and month is not None:
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
            "comment": Comment().decode(o.comment), 
            "accounts":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.pk, ))), 
            "currency": o.accounts.currency, 
        })
        initial_balance=initial_balance + o.amount
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def CreditcardsoperationsPayment(request, pk):
    creditcard=Creditcards.objects.get(pk=pk)
    dt_payment=RequestPostDtaware(request, "dt_payment")
    cco_ids=RequestPostListOfIntegers(request, "cco")
    
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

@timeit
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


@timeit
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
        iot=InvestmentsOperationsTotals_from_investment(o, timezone.now(), request.local_currency)
        percentage_invested=None if iot.io_total_current["invested_user"]==0 else  iot.io_total_current["gains_gross_user"]/iot.io_total_current["invested_user"]

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
            "daily_difference": iot.current_last_day_diff(), 
            "daily_percentage":percentage_between(o.products.basic_results()['penultimate'], o.products.basic_results()['last']), 
            "invested_user": iot.io_total_current["invested_user"], 
            "gains_user": iot.io_total_current["gains_gross_user"], 
            "balance_user": iot.io_total_current["balance_user"], 
            "currency": o.products.currency, 
            "currency_account": o.accounts.currency, 
            "percentage_invested": percentage_invested, 
            "percentage_selling_point": percentage_to_selling_point(iot.io_total_current["shares"], iot.investment.selling_price, o.products.basic_results()['last']), 
            "selling_expiration": o.selling_expiration, 
            "shares":iot.io_total_current["shares"], 
            "balance_percentage": o.balance_percentage, 
            "daily_adjustment": o.daily_adjustment, 
            "selling_price": o.selling_price, 
            "is_deletable": o.is_deletable(), 
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)



@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFull(request):
    ids=RequestGetListOfIntegers(request, "investments")
    r=[]
    for o in Investments.objects.filter(id__in=ids):
        r.append(InvestmentsOperations_from_investment(request, o, timezone.now(), request.local_currency).json())
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@api_view(['POST', ])    
@timeit
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsFullSimulation(request):
    print(request.data)
    investments=[]
    for url in request.data["investments"]:
        investments.append(obj_from_url(request, url))## Como todas deben ser iguales uso la primera
    dt=string2dtaware(request.data["dt"],  "JsUtcIso", request.local_zone)
    local_currency=request.data["local_currency"]
    temporaltable=request.data["temporaltable"]
    listdict=request.data["operations"]
    for d in listdict:
        d["datetime"]=string2dtaware(d["datetime"],  "JsUtcIso", request.local_zone)
        d["investments_id"]=investments[0].id
        d["operationstypes_id"]=id_from_url(request, d["operationstypes"])
    r=Simulate_InvestmentsOperations_from_investment(request, investments,  dt,  local_currency,  listdict,  temporaltable).json()
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def InvestmentsoperationsEvolutionChart(request):
    id=RequestGetInteger(request, "investment")
    io=InvestmentsOperations_from_investment(request, Investments.objects.get(pk=id), timezone.now(), request.local_currency)
    return JsonResponse( io.chart_evolution(), encoder=MyDjangoJSONEncoder,     safe=False)

@csrf_exempt
@transaction.atomic
@timeit
@api_view(['POST', ])    
@permission_classes([permissions.IsAuthenticated, ])
def investments_same_product_change_selling_price(request, products_id):

    if request.method == 'POST':
        form = None
        print(form)
        if form.is_valid():
            for investment_id in string2list_of_integers(form.cleaned_data['investments']):
                inv=Investments.objects.get( pk=investment_id)
                inv.selling_price=form.cleaned_data["selling_price"]
                inv.selling_expiration=form.cleaned_data["selling_expiration"]
                print(form.cleaned_data)
                print(inv)
                inv.save()
            
    ## DEBE HACERSE DESPUES DEL POST O SALEN MAS LSO DATOS
    ## Adds all active investments to iom of the same product_benchmark
    product=get_object_or_404(Products, pk=products_id)
    qs_investments=Investments.objects.filter(products_id=products_id, active=True)
    iom=InvestmentsOperationsManager_from_investment_queryset(qs_investments, timezone.now(), request)
    data=[]
    for io in iom.list:
        data.append({
            "id": io.investment.id, 
            "name":io.investment.fullName(), 
            "shares":io.current_shares(), 
            "average_price":io.current_average_price_investment().amount, 
            "balance_investment": io.current_balance_investment(), 
            "invested": io.current_invested_user(),  
            "selling_price": io.investment.selling_price,
            "selling_expiration":io.investment.selling_expiration,  
        })
    json_data=listdict2json(data)
    return render(request, 'investments_same_product_change_selling_price.html', locals())

class LeveragesViewSet(viewsets.ModelViewSet):
    queryset = Leverages.objects.all()
    serializer_class = serializers.LeveragesSerializer
    permission_classes = [permissions.IsAuthenticated]  

@timeit
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
@timeit
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsPairs(request):
    #fromyear=RequestGetInteger(request, "fromyear", date.today().year-3) 
    product_better=RequestGetUrl(request, "a")
    product_worse=RequestGetUrl(request, "b")
    
    r=[]
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

    last_pr=Percentage(0, 1)
    first_pr=common_quotes[0]["b_open"]/common_quotes[0]["a_open"]
    for row in common_quotes:#a worse, b better
        pr=row["b_open"]/row["a_open"]
        r.append({
            "datetime": dtaware_day_end_from_date(row["date"], request.local_zone), 
            "price_worse": row["a_open"], 
            "price_better": row["b_open"], 
            "price_ratio": pr, 
            "price_ratio_percentage_from_start": percentage_between(first_pr, pr), 
            "price_ratio_percentage_month_diff": percentage_between(last_pr, pr), 
            'currency':  product_better.currency, 
        })
        last_pr=pr
    
    #list_products_evolution=listdict_products_pairs_evolution_from_datetime(product_worse, product_better, common_monthly_quotes, basic_results_worse,  basic_results_better)

    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

@csrf_exempt
@timeit
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsQuotesOHCL(request):
    product=RequestGetUrl(request, "product")
    print(product)
    if product is not None:
        ld_ohcl=product.ohclDailyBeforeSplits()         
        return JsonResponse( ld_ohcl, encoder=MyDjangoJSONEncoder, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@timeit
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ProductsRanges(request):
    product=RequestGetUrl(request, "product")
    only_first=RequestGetBool(request, "only_first")
    percentage_between_ranges=RequestGetInteger(request, "percentage_between_ranges")
    if percentage_between_ranges is not None:
        percentage_between_ranges=percentage_between_ranges/1000
    percentage_gains=RequestGetInteger(request, "percentage_gains")
    if percentage_gains is not None:
        percentage_gains=percentage_gains/1000
    amount_to_invest=RequestGetInteger(request, "amount_to_invest")
    recomendation_methods=RequestGetInteger(request, "recomendation_methods")
    account=RequestGetUrl(request, "account")
    if not (product is None or only_first is None or percentage_between_ranges is None or percentage_gains is None or amount_to_invest is None or recomendation_methods is None):
        from moneymoney.productrange import ProductRangeManager
        
        prm=ProductRangeManager(request, product, percentage_between_ranges, percentage_gains, only_first,  account, decimals=product.decimals)
        prm.setInvestRecomendation(recomendation_methods)

        return JsonResponse( prm.json(), encoder=MyDjangoJSONEncoder, safe=False)
    return Response({'status': 'details'}, status=status.HTTP_400_BAD_REQUEST)
    
    
class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
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
    # if not GET, then proceed
    if "csv_file1" not in request.FILES:
        print("You must upload a file")
        return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)
    else:
        csv_file = request.FILES["csv_file1"]
        
    if not csv_file.name.endswith('.csv'):
        print('File is not CSV type')
        return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)

    #if file is too large, return
    if csv_file.multiple_chunks():
        print("Uploaded file is too big ({} MB).".format(csv_file.size/(1000*1000),))
        return Response({'status': 'details'}, status=status.HTTP_404_NOT_FOUND)

    from moneymoney.investing_com import InvestingCom
    ic=InvestingCom(request, csv_file, product=None)
    r=ic.get()
    
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
 
class QuotesViewSet(viewsets.ModelViewSet):
    queryset = Quotes.objects.all()
    serializer_class = serializers.QuotesSerializer
    permission_classes = [permissions.IsAuthenticated]  

@timeit
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
#    for d in list_:
#        print(d["total"],  last_year_balance)
        
    r={"last_year_balance": last_year_balance,  "dtaware_last_year": dtaware_last_year,  "data": list_}
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
 
 
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualIncome(request, year):
    def qs_investments_netgains_usercurrency_in_year_month(qs_investments, year, month, local_currency, local_zone):
        r =0
        #Git investments with investmentsoperations in this year, month
        dt_year_month=dtaware_month_end(year, month, local_zone)
        for investment in Investments.objects.raw("select distinct(investments.*) from investmentsoperations, investments where date_part('year', datetime)=%s and date_part('month', datetime)=%s and investments.id=investmentsoperations.investments_id", (year, month)):
            investments_operations=InvestmentsOperations_from_investment(request, investment, dt_year_month, local_currency)
            for ioh in investments_operations.io_historical:
                if ioh['dt_end'].year==year and ioh['dt_end'].month==month:
                        r=r+ioh['gains_net_user']
        return r
    
    def month_results(year,  month, month_name):
        dividends=Dividends.netgains_dividends(year, month)
        incomes=balance_user_by_operationstypes(year,  month,  eOperationType.Income, local_currency, local_zone)-dividends
        expenses=balance_user_by_operationstypes(year,  month,  eOperationType.Expense, local_currency, local_zone)

        gains=qs_investments_netgains_usercurrency_in_year_month(qs_investments, year, month, local_currency, local_zone)
        #print("Loading list netgains opt took {} (CUELLO BOTELLA UNICO)".format(timezone.now()-start))        
        
        total=incomes+gains+expenses+dividends
        
        return month_name, month,  year,  incomes, expenses, gains, dividends, total
    
    list_=[]
    futures=[]
    local_zone=request.local_zone
    local_currency=request.local_currency
    qs_investments=Investments.objects.all()
    
    
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
            #print(future, future.result())
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
    
@timeit
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
                select datetime,concepts_id, amount, comment
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
                select datetime,concepts_id, amount, comment
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
                        "comment":Comment().decode(op["comment"]), 
                        "currency": currency, 
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
            investments_operations=InvestmentsOperations_from_investment(request, investment, dt_year_month, local_currency)
            
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
    
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportAnnualGainsByProductstypes(request, year):
    local_currency=request.local_currency
    gains=cursor_rows("""
select 
    investments.id, 
    productstypes_id, 
    (investment_operations(investments.id, make_timestamp(%s,12,31,23,59,59)::timestamp with time zone, %s)).io_historical 
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

@timeit
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

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportConceptsHistorical(request):
    concept=RequestGetUrl(request, "concept")
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
    
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportDividends(request):
    qs_investments=Investments.objects.filter(active=True).select_related("products").select_related("accounts").select_related("products__leverages").select_related("products__productstypes")
    shares=cursor_rows_as_dict("investments_id", """
        select 
            investments.id as investments_id ,
            sum(shares) as shares
            from investments, investmentsoperations where active=true and investments.id=investmentsoperations.investments_id group by investments.id""")
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
        if inv.products_id in estimations:
            dps=estimations[inv.products_id]["estimation"]
            date_estimation=estimations[inv.products_id]["date_estimation"]
            percentage=Percentage(dps, quotes[inv.products_id]["last"])
            estimated=shares[inv.id]["shares"]*dps*inv.products.real_leveraged_multiplier()
        else:
            dps= 0
            date_estimation=date(date.today().year-1, 12, 31)
            percentage=0
            estimated=0
        
        
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

@timeit
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
        dividends=Dividends.net_gains_baduser_between_datetimes(dt_from, dt_to)
        incomes=0
        gains=0
        expenses=0
        list_.append({
            "year": year, 
            "balance_start": tb[year-1]["total_user"], 
            "balance_end": tb[year]["total_user"],  
            "diff": tb[year]["total_user"]-tb[year-1]["total_user"], 
            "incomes":incomes, 
            "gains_net":gains, 
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
    
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportEvolutionInvested(request, from_year):
    list_=[]
    qs=Investments.objects.all()
    for year in range(from_year, date.today().year+1): 
        iom=InvestmentsOperationsManager_from_investment_queryset(qs, dtaware_month_end(year, 12, request.local_zone), request)
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

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportsInvestmentsLastOperation(request):
    method=RequestGetInteger(request, "method", 0)
    ld=[]
    if method==0:
        investments=Investments.objects.filter(active=True).select_related("accounts").select_related("products")
        iom=InvestmentsOperationsManager_from_investment_queryset(investments, timezone.now(), request)
        
        for io in iom:
            last=io.current_last_operation_excluding_additions()
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
            })
    return JsonResponse( ld, encoder=MyDjangoJSONEncoder,     safe=False)
@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def ReportRanking(request):
    iotm=InvestmentsOperationsTotalsManager_from_all_investments(request, timezone.now())
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
        return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
    elif request.method == 'POST':
        local_currency=RequestPostString(request,"local_currency")
        local_zone=RequestPostString(request,"local_zone")
        if local_currency is not None and local_zone is not None:
            setGlobal("mem/localcurrency", local_currency)
            setGlobal("mem/localzone", local_zone)
            return JsonResponse(True, safe=False)
        return JsonResponse(False, safe=False)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, ])
@transaction.atomic
def EstimationsDps_add(request):
    print(request.data)
    year=RequestInteger(request, 'year')
    estimation=RequestDecimal(request, 'estimation')
    product=RequestUrl(request, 'product')
    print(year, estimation, product)
    if year is not None and estimation is not None  and product is not None:
        execute("delete from estimations_dps where products_id=%s and year=%s", (product.id, year))
        execute("insert into estimations_dps (date_estimation,year,estimation,source,products_id) values(%s,%s,%s,%s,%s)", (
            date.today(), year, estimation, "Internet", product.id))
        return JsonResponse(True, safe=False)
    return JsonResponse(False, safe=False)

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
def getGlobal(key, default, type="str"):
    try:
        r=cursor_one_field("select value from globals where global=%s", (key, ))
        if type=="int":
            return int(r)
        else:
            return r
    except:
        return default
    
def RequestGetBool(request, field, default=None):
    try:
        r = str2bool(request.GET.get(field))
    except:
        r=default
    return r    
def RequestPostBool(request, field, default=None):
    try:
        r = str2bool(request.POST.get(field))
    except:
        r=default
    return r    

def RequestGetInteger(request, field, default=None):
    try:
        r = int(request.GET.get(field))
    except:
        r=default
    return r
def RequestPostInteger(request, field, default=None):
    try:
        r = int(request.POST.get(field))
    except:
        r=default
    return r
def RequestInteger(request, field, default=None):
    try:
        r = int(request.data.get(field))
    except:
        r=default
    return r
    
def RequestGetString(request, field, default=None):
    try:
        r = request.GET.get(field)
    except:
        r=default
    return r

def RequestPostString(request, field, default=None):
    try:
        r = request.POST.get(field)
    except:
        r=default
    return r

def RequestGetListOfIntegers(request, field, default=None, separator=","):    
    try:
        r = string2list_of_integers(request.GET.get(field), separator)
    except:
        r=default
    return r

def RequestPostListOfIntegers(request, field, default=None,  separator=","):
    try:
        r = string2list_of_integers(request.POST.get(field), separator)
    except:
        r=default
    return r

def RequestGetDtaware(request, field, default=None):
    try:
        r = string2dtaware(request.GET.get(field), "JsUtcIso", request.local_zone)
    except:
        r=default
    return r

def RequestPostDtaware(request, field, default=None):
    try:
        r = string2dtaware(request.POST.get(field), "JsUtcIso", request.local_zone)
    except:
        r=default
    return r

def RequestPostDecimal(request, field, default=None):
    try:
        r = Decimal(request.POST.get(field))
    except:
        r=default
    return r
def RequestDecimal(request, field, default=None):
    try:
        r = Decimal(request.data.get(field))
    except:
        r=default
    return r


def obj_from_url(request, url):
    path = urllib.parse.urlparse(url).path
    resolved_func, unused_args, resolved_kwargs = resolve(path)
    class_=resolved_func.cls()
    class_.request=request
    return class_.get_queryset().get(pk=int(resolved_kwargs['pk']))
def id_from_url(request, url):
    path = urllib.parse.urlparse(url).path
    resolved_func, unused_args, resolved_kwargs = resolve(path)
    class_=resolved_func.cls()
    class_.request=request
    return int(resolved_kwargs['pk'])
 
## Returns a model obect
def RequestPostUrl(request, field,  default=None):
    try:
        r = obj_from_url(request, request.POST.get(field))
    except:
        r=default
    return r
 
## Returns a model obect
def RequestGetUrl(request, field,  default=None):
    try:
        r = obj_from_url(request, request.GET.get(field))
    except:
        r=default
    return r
 
## Returns a model obect
def RequestUrl(request, field,  default=None):
    try:
        r = obj_from_url(request, request.data.get(field))
    except:
        r=default
    return r
