from django.contrib import admin
from django.urls import path,  include
from django.conf.urls.i18n import i18n_patterns, set_language 
from django.views.generic.base import RedirectView
from django.views.i18n import JavaScriptCatalog
import debug_toolbar

from rest_framework import routers

from moneymoney import views as money_views
router = routers.DefaultRouter()
router.register(r'accounts', money_views.AccountsViewSet)
router.register(r'banks', money_views.BanksViewSet)
router.register(r'investments', money_views.InvestmentsViewSet)

urlpatterns=[
    path('api/', include(router.urls)),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
    path('login/', money_views.login, name="login"), 
    path('logout/', money_views.logout, name="logout"), 
    path('accounts/withbalance/', money_views.accounts_with_balance, name='accounts_with_balance'),
    path('banks/withbalance/', money_views.banks_with_balance, name='banks_with_balance'),
    path('investments/withbalance/', money_views.investments_with_balance, name='investments_with_balance'),
]

urlpatterns=urlpatterns+ i18n_patterns(
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('__debug__/', include(debug_toolbar.urls)),
    path('i18n/setlang/',  set_language, name="set_language"), 
    path('admin/', admin.site.urls,  name="admin-site"),

)

