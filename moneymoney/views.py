from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.http import JsonResponse
from moneymoney.investmentsoperations import InvestmentsOperations_from_investment,  InvestmentsOperationsManager_from_investment_queryset, InvestmentsOperationsTotals_from_investment
from moneymoney.reusing.connection_dj import execute, cursor_one_field, cursor_rows
from moneymoney.reusing.casts import str2bool, string2list_of_integers
from moneymoney.reusing.datetime_functions import dtaware_month_start,  dtaware_month_end, dtaware_year_end, string2dtaware
from moneymoney.reusing.listdict_functions import listdict2dict
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
    Leverages, 
    Operationstypes, 
    Orders, 
    Products, 
    Productstypes, 
    Stockmarkets, 
    Strategies, 
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

class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = Investments.objects.select_related("accounts").all()
    serializer_class = serializers.InvestmentsSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_queryset(self):
        # To get active or inactive accounts
        try:
            active = str2bool(self.request.GET.get('active'))
        except:
            active=None
        # To get all accounts of a bank
        try:
            bank_id = int(self.request.GET.get('bank'))
        except:
            bank_id=None

        if bank_id is not None:
            return self.queryset.filter(accounts__banks__id=bank_id,  active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
        else:
            return self.queryset


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
            "name":o.fullName(), 
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
            "percentage_invested": percentage_invested, 
            "percentage_selling_point": percentage_to_selling_point(iot.io_total_current["shares"], iot.investment.selling_price, o.products.basic_results()['last']), 
            "selling_expiration": o.selling_expiration, 
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
        qs=Orders.objects.filter(expiration__gt=date.today(),  executed__isnull=True).select_related("investments").select_related("investments__accounts").select_related("investments__products").select_related("investments__products__productstypes").select_related("investments__products__leverages")
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
            "investmentsname":o.investments.fullName(), 
            "currency": o.investments.products.currency, 
            "shares": o.shares, 
            "price": o.price, 
            "amount": o.shares*o.price*o.investments.products.real_leveraged_multiplier(), 
            "percentage_from_price": percentage_between(o.investments.products.basic_results()["last"], o.price),
           "executed": o.executed,  
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = serializers.ProductsSerializer
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
        for row in gains:
            if row["productstypes_id"]==pt.id:
                io_historical=eval(row["io_historical"])
                for ioh in io_historical:
                    if int(ioh["dt_end"][0:4])==year:
                        gains_net=gains_net+ioh["gains_net_user"]
                        gains_gross=gains_gross+ioh["gains_gross_user"]

        l.append({
                "id": pt.id, 
                "name":pt.name, 
                "gains_gross": gains_gross, 
                "dividends_gross":dividends_dict[pt.id]["gross"], 
                "gains_net":gains_net, 
                "dividends_net": dividends_dict[pt.id]["net"], 
        })
    return JsonResponse( l, encoder=MyDjangoJSONEncoder,     safe=False)

 
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

import urllib.parse
from django.urls import resolve

def obj_from_url(request, url):
    path = urllib.parse.urlparse(url).path
    resolved_func, unused_args, resolved_kwargs = resolve(path)
    class_=resolved_func.cls()
    class_.request=request
    return class_.get_queryset().get(pk=int(resolved_kwargs['pk']))
 
## Returns a model obect
def RequestPostUrl(request, field,  default=None):
    try:
        r = obj_from_url(request, request.POST.get(field))
    except:
        r=default
    return r
