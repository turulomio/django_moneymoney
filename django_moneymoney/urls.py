from datetime import date
from django.contrib import admin
from django.urls import path,  include
from django.conf.urls.i18n import i18n_patterns, set_language 
from django.views.generic.base import RedirectView
from django.views.i18n import JavaScriptCatalog
import debug_toolbar

from rest_framework import routers

from moneymoney import views as money_views
router = routers.DefaultRouter()
router.register(r'banks', money_views.BanksViewSet)

urlpatterns=[
    path('api/', include(router.urls)),
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
    path('login/', money_views.login, name="login"), 
    path('logout/', money_views.logout, name="logout"), 
]

urlpatterns=urlpatterns+ i18n_patterns(
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('__debug__/', include(debug_toolbar.urls)),

    path('ajax/', money_views.ajax_modal_button, name='ajax_modal_button'),
    path('ajax/investment/<int:pk>/leverage/', money_views.ajax_investment_to_json, name='ajax_investment_to_json'),

    path('i18n/setlang/',  set_language, name="set_language"), 
    path('admin/', admin.site.urls,  name="admin-site"),
    path('', money_views.home, name='home'),
    
    
    path('bank/list/', money_views.bank_list,  {'active':True}, name='bank_list_active'),
    path('bank/list/inactive/', money_views.bank_list,  {'active':False}, name='bank_list_inactive'),
    path('bank/view/<int:pk>/', money_views.bank_view, name='bank_view'),
    path('bank/new/', money_views.bank_new.as_view(), name='bank_new'),
    path('bank/update/<int:pk>', money_views.bank_update.as_view(), name='bank_update'),
    path('bank/delete/<int:pk>', money_views.bank_delete.as_view(), name='bank_delete'),

    path('account/list/', money_views.account_list,   {'active':True}, name='account_list_active'),
    path('account/list/inactive/', money_views.account_list,   {'active':False}, name='account_list_inactive'),
    path('account/view/<int:pk>/', money_views.account_view, name='account_view'),
    path('account/transfer/<int:origin>/', money_views.account_transfer, name='account_transfer'),
    path('account/transfer/delete/<str:comment>/', money_views.account_transfer_delete, name='account_transfer_delete'),
    path('account/new/<int:banks_id>/', money_views.account_new.as_view(), name='account_new'),
    path('account/update/<int:pk>/', money_views.account_update.as_view(), name='account_update'),    
    path('account/delete/<int:pk>/', money_views.account_delete.as_view(), name='account_delete'),
    
    path('accountoperation/new/<int:accounts_id>/', money_views.accountoperation_new.as_view(), name='accountoperation_new'),
    path('accountoperation/update/<int:pk>/', money_views.accountoperation_update.as_view(), name='accountoperation_update'),
    path('accountoperation/delete/<int:pk>', money_views.accountoperation_delete.as_view(), name='accountoperation_delete'),
    path('accountoperation/search/', money_views.accountoperation_search, name='accountoperation_search'),
    path('accountoperation/list/<int:pk>/<int:year>/<int:month>/', money_views.accountoperation_list, name='accountoperation_list'),
    
    path('creditcard/view/<int:pk>/', money_views.creditcard_view, name='creditcard_view'),
    path('creditcard/pay/<int:pk>/', money_views.creditcard_pay, name='creditcard_pay'),
    path('creditcard/pay/historical/<int:pk>/', money_views.creditcard_pay_historical, name='creditcard_pay_historical'),
    path('creditcard/pay/refund/<int:accountsoperations_id>/', money_views.creditcard_pay_refund, name='creditcard_pay_refund'),
    
    path('creditcard/new/<int:accounts_id>/', money_views.creditcard_new.as_view(), name='creditcard_new'),
    path('creditcard/update/<slug:pk>/', money_views.creditcard_update.as_view(), name='creditcard_update'),
    path('creditcard/delete/<slug:pk>/', money_views.creditcard_delete.as_view(), name='creditcard_delete'),
    
    
    path('creditcardoperation/new/<int:creditcards_id>', money_views.creditcardoperation_new.as_view(), name='creditcardoperation_new'),
    path('creditcardoperation/update/<int:pk>', money_views.creditcardoperation_update.as_view(), name='creditcardoperation_update'),
    path('creditcardoperation/delete/<int:pk>', money_views.creditcardoperation_delete.as_view(), name='creditcardoperation_delete'),
    
    path('dividend/new/<int:investments_id>', money_views.dividend_new.as_view(), name='dividend_new'),
    path('dividend/update/<int:pk>', money_views.dividend_update.as_view(), name='dividend_update'),
    path('dividend/delete/<int:pk>', money_views.dividend_delete.as_view(), name='dividend_delete'),
    
    
    
    path('estimations/post/', money_views.estimation_dps_new, name='estimation_dps_new'),
    

    path('investment/list/', money_views.investment_list, {'active':True}, name='investment_list_active'),
    path('investment/list/lastoperation/', money_views.investment_list_last_operation, name='investment_list_last_operation'),
    path('investment/list/lastoperation/method/<int:method>/', money_views.investment_list_last_operation_method, name='investment_list_last_operation_method'),
    path('investment/list/inactive/', money_views.investment_list, {'active': False}, name='investment_list_inactive'),
    path('investment/view/<int:pk>/', money_views.investment_view, name='investment_view'),
    path('investment/view/chart/<int:pk>/', money_views.investment_view_chart, name='investment_view_chart'),
    path('investment/new/<int:accounts_id>', money_views.investment_new.as_view(), name='investment_new'),
    path('investment/update/<int:pk>', money_views.investment_update.as_view(), name='investment_update'),
    path('investment/delete/<int:pk>', money_views.investment_delete.as_view(), name='investment_delete'),
    path('investment/change_active/<int:pk>', money_views.investment_change_active, name='investment_change_active'),
    path('investment/classes/', money_views.investment_classes, name='investment_classes'),
    path('investment/ranking/', money_views.investment_ranking, name='investment_ranking'),
    path('investment/search/', money_views.investment_search,  name='investment_search'),
    path('investment/sameproduct/changesp/<int:products_id>', money_views.investments_same_product_change_selling_price, name='investments_same_product_change_selling_price'),
    
    
    
    
    path('investment/pairs/<int:worse>/<int:better>/<int:accounts_id>/', money_views.investment_pairs, name='investment_pairs'),
    path('investment/pairs/<int:worse>/<int:better>/<int:accounts_id>/<int:amount>/', money_views.ajax_investment_pairs_invest, name='ajax_investment_pairs_invest'),
    
    path('investmentoperation/new/<int:investments_id>/', money_views.investmentoperation_new.as_view(), name='investmentoperation_new'),
    path('investmentoperation/update/<int:pk>', money_views.investmentoperation_update.as_view(), name='investmentoperation_update'),
    path('investmentoperation/delete/<int:pk>', money_views.investmentoperation_delete.as_view(), name='investmentoperation_delete'),
        
    path('order/list/', money_views.order_list, {'active':True}, name='order_list_active'),
    path('order/list/inactive/<int:year>/', money_views.order_list, {'active': False}, name='order_list_inactive'),
    path('order/new/', money_views.order_new.as_view(), name='order_new'),
    path('order/update/<int:pk>', money_views.order_update.as_view(), name='order_update'),
    path('order/delete/<int:pk>', money_views.order_delete.as_view(), name='order_delete'),
    path('order/execute/<int:pk>', money_views.order_execute, name='order_execute'),
    
    path('product/benchmark/', money_views.product_benchmark, name='product_benchmark'),
    path('product/comparation/', money_views.products_comparation, name='product_comparation'),
    path('product/comparation/', money_views.products_comparation, name='product_comparation'),
    path('product/view/<str:pk>/', money_views.product_view, name='product_view'),
    path('product/list/search/', money_views.product_list_search,  name='product_list_search'),
    path('product/list/favorites/', money_views.product_list_favorites,  name='product_list_favorites'),
    path('product/list/indexes/', money_views.product_list_indexes,  name='product_list_indexes'),
    path('product/list/cfds/', money_views.product_list_cfds,  name='product_list_cfds'),
    path('product/new/', money_views.product_new.as_view(),  name='product_new'),
    path('product/product_update/', money_views.product_update,  name='product_update'),
    path('product/ranges/', money_views.product_ranges,  name='product_ranges'),
    path('product/search/', money_views.product_search,  name='product_search'),
    path('product/chart/historical/<str:pk>/', money_views.ajax_chart_product_quotes_historical,  name='ajax_chart_product_quotes_historical'),
    path('products/pairs/<int:worse>/<int:better>/', money_views.products_pairs,  name='products_pairs'),

    path('quote/new/<str:products_id>/', money_views.quote_new.as_view(), name='quote_new'),
    path('quote/delete_last/<str:products_id>/', money_views.quote_delete_last, name='quote_delete_last'),
    path('quote/delete/', money_views.quote_delete, name='quote_delete'), #ids argument with get
    path('quote/list/<str:products_id>/', money_views.quote_list,  name='quote_list'),    
    path('quote/update/<int:pk>', money_views.quote_update.as_view(), name='quote_update'),
    
    path('concept/list/', money_views.concept_list,  name='concept_list'),
    
    path('chart/total/', money_views.ajax_chart_total, {'year_from': date.today().year},  name='ajax_chart_total'),
    path('chart/total/async/', money_views.ajax_chart_total_async, {'year_from': date.today().year},  name='ajax_chart_total_async'),
    path('chart/total/<int:year_from>/', money_views.ajax_chart_total,  name='ajax_chart_total'),

    path('report/concepts/',  money_views.report_concepts,  name='report_concepts'), 
    path('report/concepts/<int:year>/<int:month>/',  money_views.report_concepts,  name='report_concepts'), 
    path('report/concepts/historical/<int:concepts_id>/',  money_views.report_concepts_historical,  name='report_concepts_historical'), 
    path('report/dividends/',  money_views.report_dividends,  name='report_dividends'), 
    path('report/derivatives/',  money_views.report_derivatives,  name='report_derivatives'), 
    path('report/evolution/', money_views.report_evolution,  name='report_evolution'),
    path('report/export/', money_views.report_export,  name='report_export'),
    path('report/total/', money_views.report_total,  name='report_total'),
    path('report/total/income/details/<int:year>/<int:month>/', money_views.report_total_income_details,  name='report_total_income_details'),
    
    path('settings/', money_views.settings, name='settings'),
    
    path('strategy/list/', money_views.strategy_list, {'active':True}, name='strategy_list_active'),
    path('strategy/list/inactive/', money_views.strategy_list, {'active': False}, name='strategy_list_inactive'),
    path('strategy/view/<slug:pk>/', money_views.strategy_view, name='strategy_view'),
    path('strategy/new/', money_views.strategy_new.as_view(), name='strategy_new'),
    path('strategy/update/<int:pk>', money_views.strategy_update.as_view(), name='strategy_update'),
    path('strategy/delete/<int:pk>', money_views.strategy_delete.as_view(), name='strategy_delete'),
    
    
    path('widget/modal_window', money_views.widget_modal_window, name='widget_modal_window'),
    path('widget/echart', money_views.echart, name='echart'),
    
)

handler403 = 'moneymoney.views.error_403'
