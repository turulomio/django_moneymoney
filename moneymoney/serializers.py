from  moneymoney.models import Banks
from rest_framework import serializers

class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active')
        
class BanksWithBalanceSerializer(serializers.HyperlinkedModelSerializer):
    balance_accounts=serializers.SerializerMethodField()
    balance_investments=serializers.SerializerMethodField()
    balance_total=serializers.SerializerMethodField()
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'balance_accounts', 'balance_investments', 'balance_total')
        
    def get_balance_accounts(self, obj):
        return obj.balance_accounts()
    def get_balance_investments(self, obj):
        return obj.balance_investments(self.context['request'])
    def get_balance_total(self, obj):
        return obj.balance_total(self.context['request'])

