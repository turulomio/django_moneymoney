from django.contrib import admin
from django.urls import path,  include
from django.conf.urls.i18n import i18n_patterns, set_language 
from django.views.generic.base import RedirectView

from rest_framework import routers

from moneymoney import views as money_views
router = routers.DefaultRouter()
router.register(r'accounts', money_views.AccountsViewSet)
router.register(r'accountsoperations', money_views.AccountsoperationsViewSet)
router.register(r'banks', money_views.BanksViewSet)
router.register(r'creditcards', money_views.CreditcardsViewSet)
router.register(r'creditcardsoperations', money_views.CreditcardsoperationsViewSet)
router.register(r'concepts', money_views.ConceptsViewSet)
router.register(r'dividends', money_views.DividendsViewSet)
router.register(r'estimations_dps', money_views.EstimationsDpsViewSet)
router.register(r'investments', money_views.InvestmentsViewSet)
router.register(r'investmentsoperations', money_views.InvestmentsoperationsViewSet)
router.register(r'leverages', money_views.LeveragesViewSet)
router.register(r'orders', money_views.OrdersViewSet)
router.register(r'operationstypes', money_views.OperationstypesViewSet)
router.register(r'products', money_views.ProductsViewSet)
router.register(r'productstypes', money_views.ProductstypesViewSet)
router.register(r'quotes', money_views.QuotesViewSet)
router.register(r'strategies', money_views.StrategiesViewSet)
router.register(r'stockmarkets', money_views.StockmarketsViewSet)

urlpatterns=[
    path('api/', include(router.urls)),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
    path('login/', money_views.login, name="login"), 
    path('logout/', money_views.logout, name="logout"), 
    path('accounts/withbalance/', money_views.AccountsWithBalance, name='AccountsWithBalance'),
    path('accounts/transfer/', money_views.AccountTransfer, name='AccountTransfer'),
    path('accountsoperations/withbalance/', money_views.AccountsoperationsWithBalance, name='AccountsoperationsWithBalance'),
    path('creditcards/withbalance/', money_views.CreditcardsWithBalance, name='CreditcardsWithBalance'),
    path('creditcardsoperations/withbalance/', money_views.CreditcardsoperationsWithBalance, name='CreditcardsoperationsWithBalance'),
    path('creditcardsoperations/payment/<int:pk>/', money_views.CreditcardsoperationsPayment, name='CreditcardsoperationsPayment'),
    path('banks/withbalance/', money_views.BanksWithBalance, name='BanksWithBalance'),
    path('investments/withbalance/', money_views.InvestmentsWithBalance, name='InvestmentsWithBalance'),
    path('investmentsoperations/full/', money_views.InvestmentsoperationsFull, name='InvestmentsoperationsFull'),
    path('investmentsoperations/evolutionchart/', money_views.InvestmentsoperationsEvolutionChart, name='InvestmentsoperationsEvolutionChart'),
    path('orders/list/', money_views.OrdersList, name='OrdersList'),
    path('products/ranges/', money_views.ProductsRanges, name='ProductsRanges'),
    path('products/update/', money_views.ProductsUpdate, name='ProductsUpdate'),
    path('reports/annual/<int:year>/', money_views.ReportAnnual, name='ReportAnnual'),
    path('reports/annual/income/<int:year>/', money_views.ReportAnnualIncome, name='ReportAnnualIncome'),
    path('reports/annual/income/details/<int:year>/<int:month>/', money_views.ReportAnnualIncomeDetails, name='ReportAnnualIncomeDetails'),
    path('reports/dividends/', money_views.ReportDividends, name='ReportDividends'),
    path('reports/investments/lastoperation/', money_views.ReportsInvestmentsLastOperation, name='ReportsInvestmentsLastOperation'),
    path('reports/evolutionassets/<int:from_year>/', money_views.ReportEvolutionAssets, name='ReportEvolutionAssets'),
    path('reports/evolutioninvested/<int:from_year>/', money_views.ReportEvolutionInvested, name='ReportEvolutionInvested'),
    path('reports/ranking/', money_views.ReportRanking, name='ReportRanking'),
    path('reports/annual/gainsbyproductstypes/<int:year>/', money_views.ReportAnnualGainsByProductstypes, name='ReportAnnualGainsByProductstypes'),
    path('statistics/', money_views.Statistics, name='Statistics'),
    path('strategies/withbalance/', money_views.StrategiesWithBalance, name='StrategiesWithBalance'),
]
urlpatterns=urlpatterns+ i18n_patterns(
    path('i18n/setlang/',  set_language, name="set_language"), 
    path('admin/', admin.site.urls,  name="admin-site"),

)

