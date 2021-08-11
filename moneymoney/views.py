from decimal import Decimal
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from moneymoney.reusing.connection_dj import execute, cursor_one_field
from moneymoney.reusing.casts import str2bool
from moneymoney.reusing.datetime_functions import dtaware_month_start
from moneymoney.reusing.decorators import timeit
from moneymoney.reusing.percentage import Percentage,  percentage_between

from moneymoney.models import (
    Banks, 
    Accounts, 
    Accountsoperations, 
    Comment, 
    Concepts, 
    Creditcards, 
    Creditcardsoperations, 
    Investments, 
    Operationstypes, 
    percentage_to_selling_point, 
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

class OperationstypesViewSet(viewsets.ModelViewSet):
    queryset = Operationstypes.objects.all()
    serializer_class = serializers.OperationstypesSerializer
    permission_classes = [permissions.IsAuthenticated]  

class InvestmentsViewSet(viewsets.ModelViewSet):
    queryset = Investments.objects.all()
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

class AccountsViewSet(viewsets.ModelViewSet):
    queryset = Accounts.objects.all()
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
    return JsonResponse( r, encoder=MyDjangoJSONEncoder, safe=False)

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
    from moneymoney.investmentsoperations import InvestmentsOperationsTotals_from_investment
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
            "accounts__url":request.build_absolute_uri(reverse('accounts-detail', args=(o.accounts.id, ))), 
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
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)
 
 
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


 
