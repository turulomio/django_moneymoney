from decimal import Decimal
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from moneymoney.reusing.connection_dj import execute, cursor_one_field
from moneymoney.reusing.casts import str2bool
from moneymoney.reusing.decorators import timeit
from moneymoney.reusing.percentage import Percentage,  percentage_between

from moneymoney.models import (
    Banks, 
    Accounts, 
    Investments, 
    percentage_to_selling_point, 
)
from moneymoney import serializers
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions
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
            return self.queryset.filter(banks__id=bank_id,   active=True)
        elif active is not None:
            return self.queryset.filter(active=active)
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
def banks_with_balance(request):
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
def accounts_with_balance(request):
    active=RequestGetBool(request, 'active')
    bank_id=RequestGetInteger(request, 'bank')

    if bank_id is not None:
        qs=Accounts.objects.filter(banks__id=bank_id,   active=True)
    elif active is not None:
        qs=Accounts.objects.filter( active=active)
    else:
        qs=Accounts.objects.all()
            
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
        })
    return JsonResponse( r, encoder=MyDjangoJSONEncoder,     safe=False)

@timeit
@csrf_exempt
@api_view(['GET', ])    
@permission_classes([permissions.IsAuthenticated, ])
def investments_with_balance(request):
    from moneymoney.investmentsoperations import InvestmentsOperationsTotals_from_investment
    active=RequestGetBool(request, 'active', None)
    bank_id=RequestGetInteger(request, 'bank', None)

    if bank_id is not None:
        qs=Investments.objects.filter(accounts__banks__id=bank_id,   active=True)
    elif active is not None:
        qs=Investments.objects.filter( active=active)
    else:
        qs=Investments.objects.all()
            
    r=[]
    for o in qs:
        iot=InvestmentsOperationsTotals_from_investment(o, timezone.now(), request.local_currency)
        percentage_invested=None if iot.io_total_current["invested_user"]==0 else  iot.io_total_current["gains_gross_user"]/iot.io_total_current["invested_user"]

        r.append({
            "id": o.id,  
            "name":o.name, 
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


 
