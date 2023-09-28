from django.contrib import admin
from django.urls import path,  include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from moneymoney import views as money_views
from moneymoney import views_login as money_views_login
from rest_framework import routers

router = routers.DefaultRouter()
routers.DefaultRouter
router.register(r'accounts', money_views.AccountsViewSet)
router.register(r'accountsoperations', money_views.AccountsoperationsViewSet)
router.register(r'banks', money_views.BanksViewSet)
router.register(r'concepts', money_views.ConceptsViewSet)
router.register(r'creditcards', money_views.CreditcardsViewSet)
router.register(r'creditcardsoperations', money_views.CreditcardsoperationsViewSet)
router.register(r'dividends', money_views.DividendsViewSet)
router.register(r'dps', money_views.DpsViewSet)
router.register(r'estimationsdps', money_views.EstimationsDpsViewSet)
router.register(r'fastoperationscoverage', money_views.FastOperationsCoverageViewSet)
router.register(r'investments', money_views.InvestmentsViewSet)
router.register(r'investmentsoperations', money_views.InvestmentsoperationsViewSet)
router.register(r'leverages', money_views.LeveragesViewSet)
router.register(r'operationstypes', money_views.OperationstypesViewSet)
router.register(r'orders', money_views.OrdersViewSet)
router.register(r'products', money_views.ProductsViewSet)
router.register(r'productspairs', money_views.ProductspairsViewSet)
router.register(r'productstypes', money_views.ProductstypesViewSet)
router.register(r'quotes', money_views.QuotesViewSet)
router.register(r'strategies', money_views.StrategiesViewSet)
router.register(r'stockmarkets', money_views.StockmarketsViewSet)

urlpatterns=[
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
    path('alerts/', money_views.Alerts.as_view(), name='Alerts'),
    path('login/', money_views_login.login, name="login"), 
    path('logout/', money_views_login.logout, name="logout"), 
    path('accounts/transfer/', money_views.AccountTransfer, name='AccountTransfer'),
    path('assets/report/', money_views.AssetsReport, name='AssetsReport'),
    path('catalog_manager/', money_views.CatalogManager, name='CatalogManager'),
    path('currencies/', money_views.Currencies, name='Currencies'),
    path('derivatives/', money_views.Derivatives.as_view(), name='Derivatives'),
    path('investments/classes/', money_views.InvestmentsClasses.as_view(), name='InvestmentsClasses'),
    path('investments/changesellingprice/', money_views.InvestmentsChangeSellingPrice, name='InvestmentsChangeSellingPrice'),
    path('ios/', money_views.IOS, name='IOS'),
    path('maintenance/catalogs/update/', money_views.MaintenanceCatalogsUpdate, name='MaintenanceCatalogsUpdate'),
    path('products/pairs/', money_views.ProductsPairs,  name='ProductsPairs'),
    path('products/ranges/', money_views.ProductsRanges, name='ProductsRanges'),
    path('products/update/', money_views.ProductsUpdate, name='ProductsUpdate'),
    path('profile/', money_views.Profile.as_view(), name='Profile'),
    path('products/quotes/ohcl/', money_views.ProductsQuotesOHCL, name='ProductsQuotesOHCL'),
    path('quotes/massive_update/', money_views.QuotesMassiveUpdate.as_view(), name='QuotesMassiveUpdate'),
    path('recomendationmethods/', money_views.RecomendationMethods, name='RecomendationMethods'),
    path('reports/annual/<int:year>/', money_views.ReportAnnual, name='ReportAnnual'),
    path('reports/annual/income/<int:year>/', money_views.ReportAnnualIncome, name='ReportAnnualIncome'),
    path('reports/concepts/', money_views.ReportConcepts, name='ReportConcepts'),
    path('reports/annual/income/details/<int:year>/<int:month>/', money_views.ReportAnnualIncomeDetails, name='ReportAnnualIncomeDetails'),
    path('reports/dividends/', money_views.ReportDividends, name='ReportDividends'),
    path('reports/investments/lastoperation/', money_views.ReportsInvestmentsLastOperation, name='ReportsInvestmentsLastOperation'),
    path('reports/investmentsoperations/current/', money_views.ReportCurrentInvestmentsOperations, name='ReportCurrentInvestmentsOperations'),
    path('reports/evolutionassets/<int:from_year>/', money_views.ReportEvolutionAssets, name='ReportEvolutionAssets'),
    path('reports/evolutionassets/chart/', money_views.ReportEvolutionAssetsChart, name='ReportEvolutionAssetsChart'),
    path('reports/evolutioninvested/<int:from_year>/', money_views.ReportEvolutionInvested, name='ReportEvolutionInvested'),
    path('reports/ranking/', money_views.ReportRanking, name='ReportRanking'),
    path('reports/zerorisk/', money_views.ReportZeroRisk, name='ReportZeroRisk'),
    path('reports/annual/gainsbyproductstypes/<int:year>/', money_views.ReportAnnualGainsByProductstypes, name='ReportAnnualGainsByProductstypes'),
    path('statistics/', money_views.Statistics, name='Statistics'),
    path('timezones/', money_views.Timezones.as_view(), name='Timezones'),
    path('unogenerator/working/', money_views.UnogeneratorWorking.as_view()),
    
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

