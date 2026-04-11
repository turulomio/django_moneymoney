from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta
from pydicts import casts
from asgiref.sync import sync_to_async
import time
from django.core.cache import cache


def test_Quotes_model(self):
    for i in range(4):
        models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i)
        models.Quotes.objects.create(products_id=79328+i, datetime=casts.dtaware_now(),quote=i*10)

    with self.assertNumQueries(1):
        quotes=models.Quotes.qs_last_quotes()
        self.assertEqual(quotes.count(), 4)


def test_Quotes(self):
    for i in range(2):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED)

    with self.assertNumQueries(1):
        quotes=tests_helpers.client_get(self, self.client_authorized_1, f"/api/quotes/?last=true", status.HTTP_200_OK)     

def test_Quotes_ohcl(self):
    for i in range(3):
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1,datetime=casts.dtaware_now()-timedelta(days=i), products="/api/products/79228/") , status.HTTP_201_CREATED)

    with self.assertNumQueries(2):
        ohcl=tests_helpers.client_get(self, self.client_authorized_1, f"/products/quotes/ohcl/?product=/api/products/79228/", status.HTTP_200_OK)      
    self.assertEqual(len(ohcl), 3)

def test_Quotes_cache(self):
    # Limpiamos la caché del servidor para tener un entorno predecible
    cache.clear()

    # Creamos un producto de prueba
    dict_pp = tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(name="Test Cache Product"), status.HTTP_201_CREATED)
    product_id = dict_pp["id"]
    
    # Creamos una cotización con más de 1 día de antigüedad para forzar el uso de la caché del servidor (is_old=True)
    old_dt = timezone.now() - timedelta(days=5)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=10, datetime=old_dt), status.HTTP_201_CREATED)

    # Mock para simular el request con los atributos generados por el middleware QuotesCacheMiddleware
    class MockRequest:
        def __init__(self):
            self.start = timezone.now()
            self.quotes_request_count = 0
            self.quotes_hit_count = 0
            self.quotes_server_cache_hit_count = 0
            self.cache_quotes = {}

    # 1. Primera petición: Debería ir a la base de datos (L1 y L2 están vacíos)
    req1 = MockRequest()
    with self.assertNumQueries(1):
        q1 = models.Quotes.get_quote(product_id, old_dt, req1)
    self.assertIsNotNone(q1)
    self.assertEqual(req1.quotes_request_count, 1)
    self.assertEqual(req1.quotes_hit_count, 0)
    self.assertEqual(req1.quotes_server_cache_hit_count, 0)

    # 2. Segunda petición usando el MISMO request: Debería golpear la caché de la petición (L1)
    with self.assertNumQueries(0):
        q2 = models.Quotes.get_quote(product_id, old_dt, req1)
    self.assertEqual(q1, q2)
    self.assertEqual(req1.quotes_request_count, 2)
    self.assertEqual(req1.quotes_hit_count, 1)
    self.assertEqual(req1.quotes_server_cache_hit_count, 0)

    # 3. Tercera petición con un NUEVO request: L1 está vacío, pero debería golpear la caché del servidor (L2)
    req2 = MockRequest()
    with self.assertNumQueries(0):
        q3 = models.Quotes.get_quote(product_id, old_dt, req2)
    self.assertEqual(q1.id, q3.id)
    self.assertEqual(req2.quotes_request_count, 1)
    self.assertEqual(req2.quotes_hit_count, 0)
    self.assertEqual(req2.quotes_server_cache_hit_count, 1)

def test_Quotes_cache_benchmark(self):
    """
    Benchmark para medir la diferencia de rendimiento entre:
    1. Sin Caché (consultas directas a la base de datos)
    2. Caché L2 (Caché del servidor / Redis / LocMem)
    3. Caché L1 (Memoria de la petición actual dict de Python)
    """
    cache.clear()
    product_ids = []
    old_dt = timezone.now() - timedelta(days=10)
    
    # Setup: Creamos 5 productos y 5 cotizaciones antiguas
    for i in range(5):
        dict_pp = tests_helpers.client_post(self, self.client_authorized_1, "/api/products/", models.Products.post_personal_payload(name=f"Bench Product {i}"), status.HTTP_201_CREATED)
        product_ids.append(dict_pp["id"])
        tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/", models.Quotes.post_payload(products=dict_pp["url"], quote=10+i, datetime=old_dt), status.HTTP_201_CREATED)

    iterations = 200 # 200 iteraciones * 5 productos = 1000 consultas por escenario
    
    # 1. Escenario A: Sin Caché (Forzamos borrar L2 en cada iteración para forzar la lectura de DB)
    start_time = time.perf_counter()
    for _ in range(iterations):
        for pid in product_ids:
            cache.clear()
            models.Quotes.get_quote(pid, old_dt, None)
    time_no_cache = max(time.perf_counter() - start_time, 0.0001)

    # 2. Escenario B: Sólo Caché L2 (Servidor LocMem)
    cache.clear()
    start_time = time.perf_counter()
    for _ in range(iterations):
        for pid in product_ids:
            models.Quotes.get_quote(pid, old_dt, None)
    time_l2_cache = max(time.perf_counter() - start_time, 0.0001)

    # 3. Escenario C: Caché L1 (Request) + L2
    cache.clear()
    class MockRequest:
        def __init__(self):
            self.start = timezone.now()
            self.quotes_request_count = 0
            self.quotes_hit_count = 0
            self.quotes_server_cache_hit_count = 0
            self.cache_quotes = {}
    
    req = MockRequest()
    start_time = time.perf_counter()
    for _ in range(iterations):
        for pid in product_ids:
            models.Quotes.get_quote(pid, old_dt, req)
    time_l1_cache = max(time.perf_counter() - start_time, 0.0001)

    print("\n" + "="*60)
    print("📊 RESULTADOS DEL BENCHMARK DE CACHÉ DE QUOTES 📊")
    print("="*60)
    print(f"Total de consultas simuladas por escenario: {iterations * len(product_ids)}")
    print(f"🔴 Sin Caché (Sólo DB): {time_no_cache:.4f} segundos")
    print(f"🟡 Caché L2 (Servidor) : {time_l2_cache:.4f} segundos (x{time_no_cache/time_l2_cache:.2f} más rápido que DB)")
    print(f"🟢 Caché L1 (Request)  : {time_l1_cache:.4f} segundos (x{time_no_cache/time_l1_cache:.2f} más rápido que DB)")
    print(f"🚀 Ventaja L1 vs L2    : L1 es x{time_l2_cache/time_l1_cache:.2f} más rápido que L2")
    print("="*60 + "\n")

    # Comprobaciones para asegurar que la jerarquía de caché de hecho mejora el rendimiento
    self.assertTrue(time_l2_cache < time_no_cache, "La caché L2 debería ser más rápida que la base de datos")
    self.assertTrue(time_l1_cache < time_l2_cache, "La caché L1 (diccionario en memoria) debería ser más rápida que L2")
