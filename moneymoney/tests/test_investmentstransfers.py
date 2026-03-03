from pydicts import casts
from django.core.exceptions import ValidationError
from django.utils import timezone
from moneymoney import models, types
from moneymoney.tests import assert_max_queries


def test_Investmentstransfers(self):
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
