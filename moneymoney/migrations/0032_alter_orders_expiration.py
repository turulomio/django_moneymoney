# Generated by Django 4.1.7 on 2023-02-18 05:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moneymoney', '0031_data_inverting_products_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='expiration',
            field=models.DateField(blank=True, null=True),
        ),
    ]