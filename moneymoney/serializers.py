from  moneymoney.models import Accounts, Banks, Investments
from rest_framework import serializers


class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active')
        
class BanksWithBalanceSerializer(serializers.HyperlinkedModelSerializer):
    balance_accounts=serializers.SerializerMethodField()
    balance_investments=serializers.SerializerMethodField()
    balance_total=serializers.SerializerMethodField()
    is_deletable=serializers.SerializerMethodField()
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'balance_accounts', 'balance_investments', 'balance_total', 'is_deletable')
        
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

class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    accounts = AccountsSerializer( many=False, read_only=True)
    class Meta:
        model = Investments
        fields = ('url', 'name', 'active','accounts')
