# Generated by Django 4.1.5 on 2023-01-14 11:33

from django.db import migrations

## Removes all Investmentsaccounsoperations to convert them into accountsoperations

def insert_ao(apps, schema_editor):
    IAO=apps.get_model('moneymoney', 'Investmentsaccountsoperations')
    AO=apps.get_model('moneymoney', 'Accountsoperations')
    for iao in IAO.objects.all():
        iao.delete()
        ao=AO()
        ao.id=iao.id
        ao.datetime=iao.datetime
        ao.concepts=iao.concepts
        ao.amount=iao.amount
        ao.comment=iao.comment
        ao.accounts=iao.accounts
        ao.save()
        
class Migration(migrations.Migration):

    dependencies = [
        ('moneymoney', '0009_accountsoperations_operationstypes'),
    ]



    operations = [
    
        migrations.RunPython(insert_ao)
    ]