# Generated by Django 5.0.2 on 2024-03-16 05:17
# Converts old transfer. Accountsoperations with comments 10002,origin,destiny,commission ...

from django.db import migrations
from moneymoney.types import eConcept

def overrided_Accountstransfers_save(at, apps):    
    """
        Overrided saves can't be used in migrations so we have to recreate that method
    """
    Accountsoperations=apps.get_model('moneymoney', 'Accountsoperations')
    
    at.ao_origin=Accountsoperations()
    at.ao_origin.datetime=at.datetime
    at.ao_origin.accounts=at.origin
    at.ao_origin.concepts_id=eConcept.TransferOrigin
    at.ao_origin.amount=-at.amount
    at.ao_origin.comment=at.comment
    at.ao_origin.save()
    
    at.ao_destiny=Accountsoperations()
    at.ao_destiny.datetime=at.datetime
    at.ao_destiny.accounts=at.destiny
    at.ao_destiny.concepts_id=eConcept.TransferDestiny
    at.ao_destiny.amount=at.amount
    at.ao_destiny.comment=at.comment
    at.ao_destiny.save()
    
    if at.commission!=0:
        at.ao_commission=Accountsoperations()
        at.ao_commission.datetime=at.datetime
        at.ao_commission.accounts=at.origin
        at.ao_commission.concepts_id=eConcept.BankCommissions
        at.ao_commission.amount=-at.commission
        at.ao_commission.comment=at.comment
        at.ao_commission.save()

    at.save()
    at.ao_origin.associated_transfer=at
    at.ao_origin.save()
    at.ao_destiny.associated_transfer=at
    at.ao_destiny.save()
    if at.ao_commission is not None:
        at.ao_commission.associated_transfer=at
        at.ao_commission.save()


def convert_old_transfers(apps, schema_editor):
    Accountsoperations=apps.get_model('moneymoney', 'Accountsoperations')
    Accountstransfers=apps.get_model('moneymoney', 'Accountstransfers')


    for old_transfer in Accountsoperations.objects.filter(comment__startswith="10002,"):
        comment_id, old_ao_origin_id, old_ao_destiny_id, old_ao_commission_id=old_transfer.comment.split(",")
        
        #Checks all old_ao exists
        try:
            old_ao_origin=Accountsoperations.objects.get(pk=int(old_ao_origin_id))
            old_ao_destiny=Accountsoperations.objects.get(pk=int(old_ao_destiny_id))
            if int(old_ao_commission_id)==-1:
                old_ao_commission=None
            else:
                old_ao_commission=Accountsoperations.objects.get(pk=int(old_ao_commission_id))
        except:
            print("Bad transfer")
            continue
        
        
        #Create new transfer
        t=Accountstransfers()
        t.datetime=old_ao_origin.datetime
        t.origin=old_ao_origin.accounts
        t.destiny=old_ao_destiny.accounts
        t.amount=abs(old_ao_destiny.amount)
        t.commission=abs(old_ao_commission.amount) if old_ao_commission is not None else 0
        t.comment=""
        
        t.save()
        overrided_Accountstransfers_save(t, apps)
        
        old_ao_origin.delete()
        old_ao_destiny.delete()
        if old_ao_commission is not None:
            old_ao_commission.delete()

class Migration(migrations.Migration):

    dependencies = [
        ("moneymoney", "0043_accountstransfers_and_more"),
    ]

    operations = [
    
        migrations.RunPython(convert_old_transfers), 
    
    ]
