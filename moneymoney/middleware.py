from datetime import timezone

from django.utils.deprecation import MiddlewareMixin

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

    def get_quote(self, products_id, datetime):
        if (products_id, datetime) in self.cache_quotes:
            self.quotes_hit_count+=1
            self.quotes_request_count+=1
            return self.cache_quotes[(products_id, datetime)]
        else:
            self.quotes_request_count+=1
            return None




    def process_response(self, request, response):
        if hasattr(request, '_quotes_cache'):
            del request.cache_quotes
        print("Request hit count:", request.quotes_hit_count)
        print("Request request count:", request.quotes_request_count)
        print("Request time:", timezone.now()-request.start)
        return response