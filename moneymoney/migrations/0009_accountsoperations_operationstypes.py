# Generated by Django 4.1.5 on 2023-01-14 12:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('moneymoney', '0008_remove_accountsoperations_operationstypes'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountsoperations',
            name='operationstypes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='moneymoney.operationstypes'),
        ),
    ]