from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.utils import timezone
from datetime import timedelta
from pydicts import casts
from asgiref.sync import sync_to_async


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

async def test_Quotes_get_quotes_async(self):
    quotes=[]
    client_post_async = sync_to_async(tests_helpers.client_post)
    for i in range(5):
        quote = await client_post_async(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED)
        quotes.append(quote)
    #Creates a dict_tupled to query massive quotes
    lod_=[]
    fivedays=casts.dtaware_now()-timedelta(days=5)
    for quote in quotes:
        lod_.append({"products_id": 79329,  "datetime": casts.str2dtaware(quote["datetime"])})
    lod_.append({"products_id":79329,  "datetime": fivedays})#Doesn't exist
    
    # Gets quotes and checks them with quotes list
    r = await models.Quotes.async_get_quotes_with_a_methods(lod_)
    for i in range(5):
        quotes_datetime=casts.str2dtaware(quotes[i]["datetime"])
        self.assertEqual(quotes[i]["quote"], r[79329][quotes_datetime]["quote"]   )
        
    self.assertEqual(r[79329][fivedays]["quote"], None)

    # Products basic_results empty
    p = await models.Products.objects.aget(pk=79330)
    basic_results_async = sync_to_async(p.basic_results)
    self.assertIsNone((await basic_results_async())["lastyear"])


    # Products without quotes
    now=timezone.now()
    lod_=[{"products_id": 79330,  "datetime": now}, ]
    r = await models.Quotes.async_get_quotes_with_a_methods(lod_)
    self.assertIsNone(r[79330][now]["quote"])

async def test_benchmark_get_quotes(self):
    """
    Compares the performance of synchronous vs. asynchronous get_quotes.
    """
    import time
    print("\n--- Running get_quotes Benchmark ---")
    num_quotes_to_fetch = 5
    
    # 1. Prepare data
    lod_ = []
    for i in range(num_quotes_to_fetch):
        # Use different products and times to avoid caching and ensure real queries
        product_id = 79329 + (i % 5) 
        dt = timezone.now() - timedelta(days=i)
        lod_.append({"products_id": product_id, "datetime": dt})
        await models.Quotes.objects.acreate(products_id=product_id, datetime=dt, quote=i)


    # 2. Benchmark synchronous version (using ThreadPoolExecutor)
    start_time_sync = time.time()
    get_quotes_sync = sync_to_async(models.Quotes.get_quotes)
    rsync=await get_quotes_sync(lod_)
    duration_sync = time.time() - start_time_sync
    print(f"Synchronous get_quotes took: {duration_sync:.4f} seconds")

    # 3. Benchmark asynchronous version with a methods 
    # DEBERIA PROBARSE EN UN SERVIDOR ASINCRONO NO CREO QUE SEA CORRECTO
    start_time_async = time.time()
    rasync=await models.Quotes.async_get_quotes_with_a_methods(lod_)
    duration_async = time.time() - start_time_async
    print(f"Asynchronous async_get_quotes_with_a_methods took: {duration_async:.4f} seconds")

    # 4. Benchmark asynchronous version with thread pool
    start_time_asynct = time.time()
    rasynct=await sync_to_async(models.Quotes.get_quotes_with_threadpool)(lod_)
    duration_asynct = time.time() - start_time_asynct
    print(f"Asynchronous async_get_quotes with threadpool took: {duration_asynct:.4f} seconds")
    #self.assertLess(duration_async, duration_sync, "Async version should be faster than the sync (threaded) version.")
    print("------------------------------------")

    #Check everything is ok
    for d in lod_:
        # print(d["products_id"], d["datetime"],rsync[d["products_id"]][d["datetime"]]["quote"],rasync[d["products_id"]][d["datetime"]]["quote"])
        self.assertEqual(rsync[d["products_id"]][d["datetime"]]["quote"], rasync[d["products_id"]][d["datetime"]]["quote"])
        # self.assertEqual(rasync[d["products_id"]][d["datetime"]]["quote"], rasynct[d["products_id"]][d["datetime"]]["quote"]) FALLA 
    

def test_Quotes_get_quotes(self):
    quotes=[]
    for i in range(5):
        quote = tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(quote=i+1), status.HTTP_201_CREATED)
        quotes.append(quote)
    #Creates a dict_tupled to query massive quotes
    lod_=[]
    fivedays=casts.dtaware_now()-timedelta(days=5)
    for quote in quotes:
        lod_.append({"products_id": 79329,  "datetime": casts.str2dtaware(quote["datetime"])})
    lod_.append({"products_id":79329,  "datetime": fivedays})#Doesn't exist
    
    # Gets quotes and checks them with quotes list
    r = models.Quotes.get_quotes(lod_)
    for i in range(5):
        quotes_datetime=casts.str2dtaware(quotes[i]["datetime"])
        self.assertEqual(quotes[i]["quote"], r[79329][quotes_datetime]["quote"]   )
    self.assertEqual(r[79329][fivedays]["quote"], None)


    # Products basic_results empty
    p = models.Products.objects.get(pk=79330)
    self.assertIsNone(p.basic_results()["lastyear"])


    # Products without quotes
    now=timezone.now()
    lod_=[{"products_id": 79330,  "datetime": now}, ]
    r = models.Quotes.get_quotes(lod_)
    self.assertIsNone(r[79330][now]["quote"])