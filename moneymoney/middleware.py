from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from django_moneymoney import settings
from moneymoney import functions

class QuotesCacheMiddleware(MiddlewareMixin):
    """
    Middleware para implementar un caché a nivel de petición para las cotizaciones (Quotes)
    y los factores de conversión de moneda.
    Esto previene consultas redundantes a la base de datos para las mismas cotizaciones
    dentro de una única petición HTTP.

    Las llaves del caché serán tuplas (products_id, datetime) 
    El valor cacheado será un objeto models.Quotes

    """
    def process_request(self, request):
        request.start=timezone.now()
        request.quotes_request_count=0
        request.quotes_hit_count=0
        request.cache_quotes = {}

    def process_response(self, request, response):
        if hasattr(request, 'cache_quotes'):
            del request.cache_quotes
        # if hasattr(request, 'quotes_hit_count'):
        #     print("Request hit count:", request.quotes_hit_count)
        #     print("Request request count:", request.quotes_request_count)
        # if hasattr(request, 'start'):
        #     print("Request time:", timezone.now()-request.start)
        if settings.DEBUG:
            print (f"Quotes request cache: {request.quotes_hit_count}/{request.quotes_request_count}")
            functions.show_queries_function(True)
            print(f"View took {timezone.now()-request.start}")
        
        return response