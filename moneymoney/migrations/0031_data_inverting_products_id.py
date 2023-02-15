# Esta migración solo será ejecutada en instalaciones existentes, ya que los datos se cargan con loaddata_
#


from django.db import migrations
from tqdm import tqdm

def inverting_products_id(apps, schema_editor):
    Products=apps.get_model('moneymoney', 'Products')
    EDPS=apps.get_model('moneymoney', 'EstimationsDPS')
    DPS=apps.get_model('moneymoney', 'DPS')
    Investments=apps.get_model('moneymoney', 'Investments')
    Productspairs=apps.get_model('moneymoney', 'Productspairs')
    Profile=apps.get_model('moneymoney', 'Profile')
    Quotes=apps.get_model('moneymoney', 'Quotes')
    Splits=apps.get_model('moneymoney', 'Splits')
    
    #Iterate all products
    for p in tqdm(Products.objects.all()):
        oldid=p.id
        #Create new product
        new_p=p
        new_p.id=-p.id
        new_p.save()
        
        old_p=Products.objects.get(pk=oldid)

        #Update products
        DPS.objects.filter(products=old_p).update(products=new_p)
        EDPS.objects.filter(products=old_p).update(products=new_p)
        Investments.objects.filter(products=old_p).update(products=new_p)
        Productspairs.objects.filter(a=old_p).update(a=new_p)
        Productspairs.objects.filter(b=old_p).update(b=new_p)
        Quotes.objects.filter(products=old_p).update(products=new_p)
        Splits.objects.filter(products=old_p).update(products=new_p)
        
        #Searches product in profile
        for profile in Profile.objects.all():
            if old_p in profile.favorites.all():
                profile.favorites.remove(old_p)
                profile.save()
                profile.favorites.add(new_p)
                profile.save()
        old_p.delete()



class Migration(migrations.Migration):

    dependencies = [
        ('moneymoney', '0030_profile_annual_gains_target'),
    ]

    operations = [
        migrations.RunPython(inverting_products_id)
    ]
