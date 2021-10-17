from moneymoney import __version__, __versiondate__
from moneymoney.models import Globals

## FOR VIEWS AND TEMPLATES
class MoneyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
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
        globals=Globals.objects.all()
        request.globals={}
        for g in globals:
            request.globals[g.global_field.replace("/", ("__"))]=g.value
        request.local_currency=request.globals.get("mem__localcurrency", "EUR")
        request.local_zone=request.globals.get("mem__localzone",  "Europe/Madrid")
