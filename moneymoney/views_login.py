## This file belongs to https://github.com/turulomio/django_moneymoney project. If you want to reuse it pleuse copy with this reference

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from request_casting.request_casting import all_args_are_not_none, RequestString
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

@extend_schema(
    description="Method to login and get auth token", 
    examples=[
        OpenApiExample('Login example',value={"username": "username", "password":"password"})
    ],
    responses={
        200: OpenApiResponse( description="Returns an authentication token"),  
    }, 
    request={
       'application/json': OpenApiTypes.OBJECT
    },
)

@api_view(['POST'])
def login(request):
    username=RequestString(request, "username")
    password=RequestString(request, "password")
    
    if all_args_are_not_none(username, password):
        try:
            user=User.objects.get(username=username)
        except User.DoesNotExist:
            return Response("Wrong credentials", status=status.HTTP_401_UNAUTHORIZED)
            
        pwd_valid=check_password(password, user.password)
        if not pwd_valid:
            return Response("Wrong credentials", status=status.HTTP_401_UNAUTHORIZED)

        if Token.objects.filter(user=user).exists():#Lo borra
            token=Token.objects.get(user=user)
            token.delete()
        token=Token.objects.create(user=user)
        
        user.last_login=timezone.now()
        user.save()
        return Response(token.key)
    else:
        return Response("Wrong credentials", status=status.HTTP_401_UNAUTHORIZED)
    
@api_view(['POST'])
def logout(request):
    key=RequestString(request, "key")
    if all_args_are_not_none(key):
        if Token.objects.filter(key=key).exists():
            Token.objects.get(key=key).delete()
            return Response("Logged out")
    return Response("Invalid token", status=status.HTTP_403_FORBIDDEN)
