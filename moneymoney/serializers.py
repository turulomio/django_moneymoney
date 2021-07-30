from  moneymoney.models import Accounts, Banks, Investments
from rest_framework import serializers

class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active', 'id')

class AccountsSerializer(serializers.HyperlinkedModelSerializer):
    banks = BanksSerializer( many=False, read_only=True)
    class Meta:
        model = Accounts
        fields = ('url', 'name', 'active', 'number','currency','banks')



class InvestmentsSerializer(serializers.HyperlinkedModelSerializer):
    accounts = AccountsSerializer( many=False, read_only=True)
    class Meta:
        model = Investments
        fields = ('url', 'id','name', 'active','accounts')
