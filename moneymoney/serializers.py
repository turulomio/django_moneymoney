from  moneymoney.models import Accounts, Banks, Investments, percentage_to_selling_point
from rest_framework import serializers
from django.utils import timezone
from moneymoney.reusing.percentage import percentage_between


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
    last_datetime=serializers.SerializerMethodField()
    last=serializers.SerializerMethodField()
    currency=serializers.SerializerMethodField()
    daily_difference=serializers.SerializerMethodField()
    daily_percentage=serializers.SerializerMethodField()
    invested_user=serializers.SerializerMethodField()
    gains_user=serializers.SerializerMethodField()
    percentage_invested=serializers.SerializerMethodField()
    percentage_selling_point=serializers.SerializerMethodField()
    selling_expiration=serializers.SerializerMethodField()
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts', 'last_datetime',  'last', 'daily_difference','daily_percentage', 'invested_user', 'gains_user','balance_user', 'currency', 'percentage_invested', 'percentage_selling_point', 'selling_expiration')
        
    def __init__(self, *args, **kwargs):
        super(InvestmentsWithBalanceSerializer, self).__init__(*args, **kwargs)
        self._dict_iot={}
        from moneymoney.investmentsoperations import InvestmentsOperationsTotals_from_investment
        if len(args)==0:
            print('NOSE')
            return
        for o in args[0]:
            self._dict_iot[o.id]=InvestmentsOperationsTotals_from_investment(o, timezone.now(), self.context['request'].local_currency)
    def get_balance_user(self, obj):
        return self._dict_iot[obj.id].io_total_current["balance_user"]    
    def get_last_datetime(self, obj):
        return self._dict_iot[obj.id].investment.products.basic_results()['last_datetime']
    def get_last(self, obj):
        return self._dict_iot[obj.id].investment.products.basic_results()['last']
    def get_daily_difference(self, obj):
        return self._dict_iot[obj.id].current_last_day_diff()
    def get_daily_percentage(self, obj):
        return percentage_between(self._dict_iot[obj.id].investment.products.basic_results()['penultimate'], self._dict_iot[obj.id].investment.products.basic_results()['last']).value
    def get_currency(self, obj):
        return self._dict_iot[obj.id].investment.products.currency
    def get_invested_user(self, obj):
        return self._dict_iot[obj.id].io_total_current["invested_user"]    
    def get_gains_user(self, obj):
        return self._dict_iot[obj.id].io_total_current["gains_gross_user"]    
    def get_percentage_invested(self, obj):
        if self._dict_iot[obj.id].io_total_current["invested_user"]!=0:
            return self._dict_iot[obj.id].io_total_current["gains_gross_user"]/self._dict_iot[obj.id].io_total_current["invested_user"]
        return None

    def get_selling_expiration(self, obj):
        return self._dict_iot[obj.id].investment.selling_expiration
    def get_percentage_selling_point(self, obj):
        return percentage_to_selling_point(self._dict_iot[obj.id].io_total_current["shares"], self._dict_iot[obj.id].investment.selling_price, self._dict_iot[obj.id].investment.products. basic_results()['last']).value                    
