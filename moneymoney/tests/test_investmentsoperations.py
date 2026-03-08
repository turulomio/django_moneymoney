from moneymoney import models
from moneymoney import types
from pydicts import casts
from django.core.exceptions import ValidationError
from django.utils import timezone
from moneymoney.reusing import tests_helpers
from request_casting.request_casting import id_from_url
from rest_framework import status

def test_Investmentsoperations(self):        
    # Create an investment operation
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(), status.HTTP_201_CREATED)
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(), status.HTTP_201_CREATED)
    dict_io=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)#Al actualizar ao asociada ejecuta otro plio
    
    # Checks exists associated_ao
    self.assertEqual(models.Accountsoperations.objects.get(pk=id_from_url(dict_io["associated_ao"])).investmentsoperations.id, dict_io["id"])#Comprueba que existe ao
    # Checks associated_ao exists in dict_io and in accounsoperation table
    self.assertIsNotNone(dict_io["associated_ao"])
    self.assertTrue(models.Accountsoperations.objects.filter(pk=id_from_url(dict_io["associated_ao"])).exists())

    # Update io        
    dict_io_updated=tests_helpers.client_put(self, self.client_authorized_1, dict_io["url"], models.Investmentsoperations.post_payload(dict_investment["url"], shares=10000), status.HTTP_200_OK)
    self.assertIsNotNone(dict_io_updated["associated_ao"], "Associated account operation should exist")
    self.assertTrue(models.Accountsoperations.objects.filter(pk=id_from_url(dict_io_updated["associated_ao"])).exists(), "Associated account operation should exist")

    
    # Delete io
    self.client_authorized_1.delete(dict_io_updated["url"])
    self.assertFalse(models.Investmentsoperations.objects.filter(pk=dict_io_updated["id"]).exists(), "Investments operation should not exist")
    self.assertFalse(models.Accountsoperations.objects.filter(pk=id_from_url(dict_io_updated["associated_ao"])).exists(), "Associated account operation should not exist")

    # Query investments operations with and investment without quotes 79226
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/", models.Investments.post_payload(products="/api/products/79226/"), status.HTTP_201_CREATED)
    self.assertEqual(models.Quotes.objects.filter(products_id=79226).count(), 0)
    response=tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(investments=dict_investment["url"]), status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response["__all__"][0], "Investment operation can't be created because its related product hasn't quotes.")



def test_Investmentsoperations_models(self):
    # Create investments
    inv=models.Investments()
    inv.name="Investment to test investments operations"
    inv.active=True
    inv.accounts_id=4
    inv.products_id=81718 #Index
    inv.selling_price=0
    inv.daily_adjustment=False
    inv.balance_percentage=100
    inv.full_clean()
    inv.save()

    # Create investment operation
    io=models.Investmentsoperations()
    io.datetime=timezone.now()
    io.operationstypes_id=types.eOperationType.SharesPurchase
    io.investments=inv
    io.price=10
    io.shares=100
    io.commission=1
    io.taxes=1
    io.currency_conversion=1
    io.comment="Testing"
    with self.assertRaises(ValidationError) as cm:
        io.full_clean()
    self.assertEqual("Investment operation can't be created because its related product hasn't quotes.", cm.exception.message_dict['__all__'][0])

    #Adds a quote
    models.Quotes.objects.create(products_id=inv.products_id, datetime=casts.dtaware_now(),quote=10)

    # Creates now investment wich product has a quoite
    io.full_clean()
    io.save()

    # Check associated_ao exists
    self.assertEqual(io.associated_ao.amount, -1002)

    # Now i change operations type to AddShares
    io.operationstypes_id=types.eOperationType.SharesAdd
    io.full_clean()
    io.save()
    self.assertEqual(io.associated_ao.amount, -2)

    #Now I remove commissions and taxes
    io.commission=0
    io.taxes=0
    io.full_clean()
    io.save()
    self.assertEqual(io.associated_ao, None)
