# Generated by Django 5.0.4 on 2024-04-28 06:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("moneymoney", "0053_migrate_from_pci_to_productstrategies"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="products",
            name="pci",
        ),
    ]