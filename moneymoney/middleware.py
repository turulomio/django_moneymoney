from moneymoney import __version__, __versiondate__
from moneymoney.models import Globals, Operationstypes
from moneymoney.reusing.currency import currency_symbol
from moneymoney.templatetags.mymenu import Menu, Action,  Group
from django.utils.translation import gettext_lazy as _

## FOR VIEWS AND TEMPLATES
class MoneyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

        self.menu=Menu(_("Django Money"))
        self.menu.append(Action(_("Banks"), None,  "bank_list_active",  True))
        self.menu.append(Action(_("Accounts"), None,  "account_list_active",  True))
        self.menu.append(Action(_("Investments"), None,  "investment_list_active",  True))
        self.menu.append(Action(_("Orders"), None,  "order_list_active",  True))
        
        grCharts=Group(2,  _("Charts"), "11", True)
        grCharts.append(Action(_("Total"), None, "ajax_chart_total", True))
        grCharts.append(Action(_("Investments classes"), None, "investment_classes", True))
        
        grReport=Group(1, _("Reports"), "10",  True)
        grReport.append(Action(_("Concepts"), None, "report_concepts", True))
        grReport.append(Action(_("Investment last operation"), None, "investment_list_last_operation", True))
        grReport.append(Action(_("Total"), None, "report_total", True))
        grReport.append(Action(_("Dividends"), None, "report_dividends", True))
        grReport.append(Action(_("Derivatives"), None, "report_derivatives", True))
        grReport.append(Action(_("Evolution"), None, "report_evolution", True))
        grReport.append(Action(_("Ranges"), None, "product_ranges", True))
        grReport.append(Action(_("Investments ranking"), None, "investment_ranking", True))
        grReport.append(Action(_("Export"), None, "report_export", True))
        grReport.append(grCharts)

        grAdministration=Group(1, _("Management"), "20",  True)
        grAdministration.append(Action(_("Concepts"), None, "concept_list", True))
        
        grProducts=Group(1, _("Products"), "30",  True)
        grProducts.append(Action(_("Update quotes"), None, "product_update", True))
        grProducts.append(Action(_("Search"), None, "product_list_search", True))
        grProducts.append(Action(_("Comparation"), None, "product_comparation", True))
        grProducts.append(Action(_("New product"), None, "product_new", True))
        
        grProductsPredefined=Group(2, _("Predefined"), "40", True)
        grProductsPredefined.append(Action(_("Benchmark index"), None, "product_benchmark", True))
        grProductsPredefined.append(Action(_("CFDs"), None, "product_list_cfds", True))
        grProductsPredefined.append(Action(_("Favorites"), None, "product_list_favorites", True))
        grProductsPredefined.append(Action(_("Indexes"), None, "product_list_indexes", True))
        
        grProducts.append(grProductsPredefined)
        
        
        self.menu.append(grProducts)
        self.menu.append(grReport)
        self.menu.append(Action(_("Strategies"), None,  "strategy_list_active",  True))
        self.menu.append(grAdministration)
        
        
        self.dict_operationstypes=Operationstypes.dictionary()


    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    
    
    def process_view(self, request, view_func, *view_args, **view_kwargs):
        request.VERSION=__version__
        request.VERSIONDATE=__versiondate__
        request.menu=self.menu
        request.operationstypes=self.dict_operationstypes
        globals=Globals.objects.all()
        request.globals={}
        for g in globals:
            request.globals[g.global_field.replace("/", ("__"))]=g.value
        request.local_currency=request.globals["mem__localcurrency"]
        request.local_zone=request.globals["mem__localzone"]
        request.local_currency_symbol=currency_symbol(request.globals["mem__localcurrency"])
