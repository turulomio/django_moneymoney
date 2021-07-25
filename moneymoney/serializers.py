from  money.models import Banks
from rest_framework import serializers

class BanksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Banks
        fields = ('url', 'name', 'active')
