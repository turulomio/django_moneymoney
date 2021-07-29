from  moneymoney.models import Accounts, Banks, Investments
from rest_framework import serializers
from django.utils import timezone


class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'id')
        
class BanksWithBalanceSerializer(serializers.HyperlinkedModelSerializer):
    balance_accounts=serializers.SerializerMethodField()
    balance_investments=serializers.SerializerMethodField()
    balance_total=serializers.SerializerMethodField()
    is_deletable=serializers.SerializerMethodField()
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'id','balance_accounts', 'balance_investments', 'balance_total', 'is_deletable')
        
    def get_balance_accounts(self, obj):
        return obj.balance_accounts()
    def get_balance_investments(self, obj):
        return obj.balance_investments(self.context['request'])
    def get_balance_total(self, obj):
        return obj.balance_total(self.context['request'])
    def get_is_deletable(self, obj):
        return obj.is_deletable()


class AccountsSerializer(serializers.HyperlinkedModelSerializer):
    banks = BanksSerializer( many=False, read_only=True)
    class Meta:
        model = Accounts
        fields = ('url', 'name', 'active', 'number','currency','banks')

class AccountsWithBalanceSerializer(serializers.HyperlinkedModelSerializer):
    balance_account=serializers.SerializerMethodField()
    balance_user=serializers.SerializerMethodField()
    banks = BanksSerializer( many=False, read_only=True)

    def __init__(self, *args, **kwargs):
        super(AccountsWithBalanceSerializer, self).__init__(*args, **kwargs)
        self._dict_balances={}
        for o in args[0]:
            self._dict_balances[o.id]=o.balance(timezone.now(),self.context['request'].local_currency ) 
        
    class Meta:
        model = Accounts
        fields = ('url', 'name', 'active', 'number','currency','banks', 'balance_account', 'balance_user')


    def get_balance_account(self, obj):
        return self._dict_balances[obj.id][0]

    def get_balance_user(self, obj):
        return self._dict_balances[obj.id][1]

class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    accounts = AccountsSerializer( many=False, read_only=True)
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts')
        
class InvestmentsWithBalanceSerializer(serializers.HyperlinkedModelSerializer):
    accounts = AccountsSerializer( many=False, read_only=True)
    balance_user=serializers.SerializerMethodField()
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts', 'balance_user')
        
    def __init__(self, *args, **kwargs):
        super(InvestmentsWithBalanceSerializer, self).__init__(*args, **kwargs)
        self._dict_iot={}
        from moneymoney.investmentsoperations import InvestmentsOperationsTotals_from_investment
        if len(args)==0:
            print('NOSE')
            return
        for o in args[0]:
            self._dict_iot[o.id]=InvestmentsOperationsTotals_from_investment(o, timezone.now(), self.context['request'].local_currency)
            print(self._dict_iot[o.id])
    def get_balance_user(self, obj):
        return self._dict_iot[obj.id].io_total_current["balance_user"]
    
#    def get_auxiliar_data(self, obj):
#        from moneymoney.investmentsoperations import InvestmentsOperations_from_investment
#        if hasattr(self, "_iotm") is False:
#            print("HOLA iotm")
#            self._iotm=InvestmentsOperations_from_investment(self.context['request'],  obj, timezone.now(), self.context['request'].local_currency):obj.balance(timezone.now(),self.context['request'].local_currency )  
#
#            def listdict_active(self):
#        list_=[]
#        
#        self.iotm=InvestmentsOperationsTotalsManager_from_investment_queryset(self.qs, timezone.now(), self.request)
#                
#        for iot in self.iotm:
#            basic_quotes=iot.investment.products.basic_results()
#            list_.append({
#                    "id": iot.investment.id, 
#                    "active":iot.investment.active, 
#                    "name": iot.investment.fullName(), 
#                    "last_datetime": basic_quotes['last_datetime'], 
#                    "last_quote": basic_quotes['last'], 
#                    "daily_difference": iot.current_last_day_diff(), 
#                    "daily_percentage":percentage_between(basic_quotes['penultimate'], basic_quotes['last']),             
#                    "invested_local": iot.io_total_current["invested_user"], 
#                    "balance": iot.io_total_current["balance_user"], 
#                    "gains": iot.io_total_current["gains_gross_user"],  
#                    "percentage_invested": Percentage(iot.io_total_current["gains_gross_user"], iot.io_total_current["invested_user"]), 
#                    "percentage_sellingpoint": percentage_to_selling_point(iot.io_total_current["shares"], iot.investment.selling_price, basic_quotes['last']), 
#                    "selling_expiration": iot.investment.selling_expiration, 
#                    "currency": iot.investment.products.currency
#                }
#            )
#        return list_
