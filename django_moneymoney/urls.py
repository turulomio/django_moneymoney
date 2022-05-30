from django.urls import path,  include
from django.conf.urls.i18n import i18n_patterns, set_language 
from django.views.generic.base import RedirectView
from django.contrib import admin

from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from moneymoney import views as money_views
from moneymoney import views_login as money_views_login
router = routers.DefaultRouter()
router.register(r'accounts', money_views.AccountsViewSet)
router.register(r'accountsoperations', money_views.AccountsoperationsViewSet)
router.register(r'banks', money_views.BanksViewSet)
router.register(r'creditcards', money_views.CreditcardsViewSet)
router.register(r'creditcardsoperations', money_views.CreditcardsoperationsViewSet)
router.register(r'concepts', money_views.ConceptsViewSet)
router.register(r'dividends', money_views.DividendsViewSet)
router.register(r'dps', money_views.DpsViewSet)
router.register(r'investments', money_views.InvestmentsViewSet)
router.register(r'investmentsoperations', money_views.InvestmentsoperationsViewSet)
router.register(r'leverages', money_views.LeveragesViewSet)
router.register(r'orders', money_views.OrdersViewSet)
router.register(r'operationstypes', money_views.OperationstypesViewSet)
router.register(r'products', money_views.ProductsViewSet)
router.register(r'productspairs', money_views.ProductspairsViewSet)
router.register(r'productstypes', money_views.ProductstypesViewSet)
router.register(r'quotes', money_views.QuotesViewSet)
router.register(r'strategies', money_views.StrategiesViewSet)
router.register(r'stockmarkets', money_views.StockmarketsViewSet)

urlpatterns=[
    path('api/', include(router.urls)),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
    path('admin/', admin.site.urls),
    path('login/', money_views_login.login, name="login"), 
    path('logout/', money_views_login.logout, name="logout"), 
    path('accounts/withbalance/', money_views.AccountsWithBalance, name='AccountsWithBalance'),
    path('accounts/transfer/', money_views.AccountTransfer, name='AccountTransfer'),
    path('accountsoperations/withbalance/', money_views.AccountsoperationsWithBalance, name='AccountsoperationsWithBalance'),
    path('assets/report/', money_views.AssetsReport, name='AssetsReport'),
    path('catalog_manager/', money_views.CatalogManager, name='CatalogManager'),
    path('creditcards/withbalance/', money_views.CreditcardsWithBalance, name='CreditcardsWithBalance'),
    path('creditcards/payments/', money_views.CreditcardsPayments, name='CreditcardsPayments'),
    path('creditcardsoperations/withbalance/', money_views.CreditcardsoperationsWithBalance, name='CreditcardsoperationsWithBalance'),
    path('creditcardsoperations/payment/<int:pk>/', money_views.CreditcardsoperationsPayments, name='CreditcardsoperationsPayments'),
    path('creditcardsoperations/payment/refund/', money_views.CreditcardsoperationsPaymentsRefund, name='CreditcardsoperationsPaymentsRefund'),
    path('concepts/migration/', money_views.ConceptsMigration, name='ConceptsMigration'),
    path('concepts/used/', money_views.ConceptsUsed, name='ConceptsUsed'),
    path('banks/withbalance/', money_views.BanksWithBalance, name='BanksWithBalance'),
    path('estimations/dps/add/', money_views.EstimationsDps_add, name='EstimationsDps_add'),
    path('estimations/dps/delete/', money_views.EstimationsDps_delete, name='EstimationsDps_delete'),
    path('estimations/dps/list/', money_views.EstimationsDps_list, name='EstimationsDps_list'),
    path('binary/to/global/', money_views.Binary2Global, name='Binary2Global'),
    path('investments/classes/', money_views.InvestmentsClasses, name='InvestmentsClasses'),
    path('investments/withbalance/', money_views.InvestmentsWithBalance, name='InvestmentsWithBalance'),
    path('investments/changesellingprice/', money_views.InvestmentsChangeSellingPrice, name='InvestmentsChangeSellingPrice'),
    path('investmentsoperations/full/', money_views.InvestmentsoperationsFull, name='InvestmentsoperationsFull'),
    path('investmentsoperations/full/simulation/', money_views.InvestmentsoperationsFullSimulation, name='InvestmentsoperationsFullSimulation'),
    path('investmentsoperations/evolutionchart/', money_views.InvestmentsoperationsEvolutionChart, name='InvestmentsoperationsEvolutionChart'),
    path('investmentsoperationstotalmanager/investments/sameproduct/', money_views.InvestmentsOperationsTotalManager_investments_same_product, name='InvestmentsOperationsTotalManager_investments_same_product'),
    path('orders/list/', money_views.OrdersList, name='OrdersList'),
    path('products/favorites/', money_views.ProductsFavorites, name='ProductsFavorites'),
    path('products/information/', money_views.ProductsInformation, name='ProductsInformation'),
    path('products/pairs/', money_views.ProductsPairs,  name='ProductsPairs'),
    path('products/ranges/', money_views.ProductsRanges, name='ProductsRanges'),
    path('products/catalog/update/', money_views.ProductsCatalogUpdate, name='ProductsCatalogUpdate'),
    path('products/update/', money_views.ProductsUpdate, name='ProductsUpdate'),
    path('products/quotes/ohcl/', money_views.ProductsQuotesOHCL, name='ProductsQuotesOHCL'),
    path('recomendationmethods/', money_views.RecomendationMethods, name='RecomendationMethods'),
    path('reports/annual/<int:year>/', money_views.ReportAnnual, name='ReportAnnual'),
    path('reports/annual/income/<int:year>/', money_views.ReportAnnualIncome, name='ReportAnnualIncome'),
    path('reports/concepts/', money_views.ReportConcepts, name='ReportConcepts'),
    path('reports/concepts/historical/', money_views.ReportConceptsHistorical, name='ReportConceptsHistorical'),
    path('reports/annual/income/details/<int:year>/<int:month>/', money_views.ReportAnnualIncomeDetails, name='ReportAnnualIncomeDetails'),
    path('reports/dividends/', money_views.ReportDividends, name='ReportDividends'),
    path('reports/investments/lastoperation/', money_views.ReportsInvestmentsLastOperation, name='ReportsInvestmentsLastOperation'),
    path('reports/investmentsoperations/current/', money_views.ReportCurrentInvestmentsOperations, name='ReportCurrentInvestmentsOperations'),
    path('reports/evolutionassets/<int:from_year>/', money_views.ReportEvolutionAssets, name='ReportEvolutionAssets'),
    path('reports/evolutionassets/chart/', money_views.ReportEvolutionAssetsChart, name='ReportEvolutionAssetsChart'),
    path('reports/evolutioninvested/<int:from_year>/', money_views.ReportEvolutionInvested, name='ReportEvolutionInvested'),
    path('reports/ranking/', money_views.ReportRanking, name='ReportRanking'),
    path('reports/annual/gainsbyproductstypes/<int:year>/', money_views.ReportAnnualGainsByProductstypes, name='ReportAnnualGainsByProductstypes'),
    path('settings/', money_views.Settings, name='Settings'),
    path('statistics/', money_views.Statistics, name='Statistics'),
    path('strategies/simulation/', money_views.StrategiesSimulation, name='StrategiesSimulation'),
    path('strategies/withbalance/', money_views.StrategiesWithBalance, name='StrategiesWithBalance'),
    path('time/', money_views.Time.as_view(), name='Time'),
    path('timezones/', money_views.Timezones.as_view(), name='Timezones'),
    

    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    
    
]

urlpatterns=urlpatterns+ i18n_patterns(
    path('i18n/setlang/',  set_language, name="set_language"), 
)

