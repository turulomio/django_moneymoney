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
        request.cache_quotes = {}

    def process_response(self, request, response):
        if hasattr(request, '_quotes_cache'):
            del request.cache_quotes
        return response