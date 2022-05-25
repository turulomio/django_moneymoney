## This file belongs to https://github.com/turulomio/django_moneymoney project. If you want to reuse it pleuse copy with this reference

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.utils import timezone
from moneymoney.request_casting import all_args_are_not_none, RequestString
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def login(request):
    username=RequestString(request, "username")
    password=RequestString(request, "password")
    
    if all_args_are_not_none(username, password):
        try:
            user=User.objects.get(username=username)
        except User.DoesNotExist:
            return Response("Wrong credentials")
            
        pwd_valid=check_password(password, user.password)
        if not pwd_valid:
            return Response("Wrong credentials")

        if Token.objects.filter(user=user).exists():#Lo borra
            token=Token.objects.get(user=user)
            token.delete()
        token=Token.objects.create(user=user)
        
        user.last_login=timezone.now()
        user.save()
        return Response(token.key)
    else:
        return Response("Wrong credentials")
    
@api_view(['POST'])
def logout(request):
    key=RequestString(request, "key")
    if all_args_are_not_none(key):
        if Token.objects.filter(key=key).exists():
            Token.objects.get(key=key).delete()
            return Response("Logged out")
    return Response("Invalid token")
