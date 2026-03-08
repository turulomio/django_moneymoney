from pydicts import casts
from django.core.exceptions import ValidationError
from django.utils import timezone
from moneymoney import models, types
from moneymoney.tests import assert_max_queries
from moneymoney.reusing import tests_helpers
from rest_framework import status
from request_casting.request_casting import id_from_url

def test_Investmentstransfers_models(self):
    # Add needed quotes for this test
    models.Quotes.objects.create(products_id=81718, datetime=casts.dtaware_now(),quote=10)
    models.Quotes.objects.create(products_id=81719, datetime=casts.dtaware_now(),quote=10)

    # Update products decimals
    models.Products.objects.filter(id__in=[81718, 81719]).update(decimals=6)

    # Create investments
    origin=models.Investments()
    origin.name="Investment origin"
    origin.active=True
    origin.accounts_id=4
    origin.products_id=79329 #Index
    origin.selling_price=0
    origin.daily_adjustment=False
    origin.balance_percentage=100
    origin.decimals=6
    origin.full_clean()
    origin.save()


    destiny=models.Investments()
    destiny.name="Investment destiny"
    destiny.active=True
    destiny.accounts_id=4
    destiny.products_id=81718 #Fund
    destiny.selling_price=0
    destiny.daily_adjustment=False
    destiny.balance_percentage=100
    destiny.decimals=6
    destiny.full_clean()
    destiny.save()

    # Create investment transfer
    it=models.Investmentstransfers()
    it.datetime_origin=timezone.now()
    it.investments_origin=origin
    it.shares_origin=100
    it.price_origin=10
    it.datetime_destiny=timezone.now()
    it.investments_destiny=destiny
    it.shares_destiny=1000
    it.price_destiny=1
    it.comment="Test investment transfer"

    #Fails due to the ValidationError
    with self.assertRaises(ValidationError) as cm:
        it.full_clean()
    self.assertEqual("Investment transfer can't be created if products types are not the same", cm.exception.message_dict['__all__'][0])

    # Tries to transfer to same origin and destiny
    it.investments_origin=destiny
    with self.assertRaises(ValidationError) as cm:
        it.full_clean()
    self.assertEqual("Investment transfer can't be created if investments are the same", cm.exception.message_dict['__all__'][0])

    # Tries to transfer with origin shares and destiny shares with the same sign
    it.investments_origin=origin# To avoid upper error
    origin.products_id=81719 # Now both are funds and different investments
    origin.full_clean()
    origin.save()
    with self.assertRaises(ValidationError) as cm:
        it.full_clean()
    self.assertEqual("Shares amount can't be of the same sign", cm.exception.message_dict['__all__'][0])

    
    it.shares_origin=-100 # To avoid upper error
    it.full_clean()
    it.save()

    # Checks investments operations
    io_origin=models.Investmentsoperations.objects.get(associated_it=it, operationstypes_id=types.eOperationType.TransferSharesOrigin)
    io_destiny=models.Investmentsoperations.objects.get(associated_it=it, operationstypes_id=types.eOperationType.TransferSharesDestiny)




def test_Investmentstransfers(self): 
    # Create needed quotes for io
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products="/api/products/81718/"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products="/api/products/81719/"), status.HTTP_201_CREATED)

    # Create an investment origin, destiny and origin io
    dict_investment_origin=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(products="/api/products/81718/"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment_origin["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    dict_investment_destiny=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(products="/api/products/81719/"), status.HTTP_201_CREATED)


    # Fails due to same sign in shares
    response=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", models.Investmentstransfers.post_payload(shares_origin=10, shares_destiny=10, investments_origin=dict_investment_origin["url"], investments_destiny=dict_investment_destiny["url"]), status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response["__all__"][0], "Shares amount can't be of the same sign")

    # Tries to transfer to same origin and destiny
    response=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", models.Investmentstransfers.post_payload(investments_origin=dict_investment_origin["url"], investments_destiny=dict_investment_origin["url"]), status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response["__all__"][0], "Investment transfer can't be created if investments are the same")

    # Create transfer
    dict_it=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentstransfers/", models.Investmentstransfers.post_payload(investments_origin=dict_investment_origin["url"], investments_destiny=dict_investment_destiny["url"]), status.HTTP_201_CREATED)
    self.assertTrue(models.Investmentstransfers.objects.filter(pk=dict_it["id"]).exists(), "Investment transfer should exist")
    self.assertTrue(models.Investmentsoperations.objects.filter(pk=id_from_url(dict_it["origin_investmentoperation"])).exists(), "Origin investment operation should exist")
    self.assertTrue(models.Investmentsoperations.objects.filter(pk=id_from_url(dict_it["destiny_investmentoperation"])).exists(), "Destiny investment operation should exist")

    # Queries all investments transfer for a given investment
    with assert_max_queries(self, 4):
        dict_its=tests_helpers.client_get(self, self.client_authorized_1, f"/api/investmentstransfers/?investments={dict_investment_origin['id']}", status.HTTP_200_OK)
        self.assertEqual(len(dict_its), 1)

    # Converts investment transfer to unifinished transfer setting datetime_destiny to null
    payload_unfinished=dict_it.copy()
    payload_unfinished["datetime_destiny"]=None
    dict_it_unfinished=tests_helpers.client_put(self, self.client_authorized_1, payload_unfinished["url"], payload_unfinished, status.HTTP_200_OK)
    self.assertEqual(dict_it_unfinished["finished"], False)
    self.assertEqual(dict_it_unfinished["destiny_investmentoperation"], None)
    
    # Tries to set null origin datetime and should fail
    payload_origin_datetime_null=dict_it.copy()
    payload_origin_datetime_null["datetime_origin"]=None
    response=tests_helpers.client_put(self, self.client_authorized_1, payload_origin_datetime_null["url"], payload_origin_datetime_null, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response["datetime_origin"][0], "This field may not be null.") 

    # Converts again dict_it_unfinished to dict_it_finished
    payload_finished=payload_unfinished.copy()
    payload_finished["datetime_destiny"]=timezone.now() 
    dict_it_finished=tests_helpers.client_put(self, self.client_authorized_1, payload_finished["url"], payload_finished, status.HTTP_200_OK)
    self.assertEqual(dict_it_finished["finished"], True)