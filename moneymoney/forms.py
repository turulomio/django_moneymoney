from django import forms
        
from moneymoney.models import Accounts, Products, RANGE_RECOMENDATION_CHOICES



class AccountsTransferForm(forms.Form):
    datetime = forms.DateTimeField(required=True)
    destiny = forms.ModelChoiceField(queryset=Accounts.objects.all().filter(active=True), required=True)
    destiny.queryset=Accounts.queryset_active_order_by_fullname()
    amount=forms.DecimalField(min_value=0, decimal_places=2, required=True)
    commission=forms.DecimalField(min_value=0, decimal_places=2, required=True)


class CreditCardPayForm(forms.Form):
    datetime= forms.DateTimeField(required=True)
    operations_id=forms.CharField(        widget=forms.HiddenInput())
    amount=forms.DecimalField(widget=forms.HiddenInput())

class ProductsRangeForm(forms.Form):
    products = forms.ModelChoiceField(queryset=Products.qs_products_of_active_investments(), required=True)
    percentage_between_ranges = forms.DecimalField(min_value=0, decimal_places=2, required=True)
    percentage_gains=forms.DecimalField(min_value=0, decimal_places=2, required=True)
    amount_to_invest=forms.DecimalField(min_value=0, decimal_places=2, required=True)
    recomendation_methods = forms.ChoiceField(choices=RANGE_RECOMENDATION_CHOICES, required=True)
    only_first=forms.BooleanField(required=False)
    accounts = forms.ModelChoiceField(queryset=Accounts.queryset_active_order_by_fullname(), required=False)
    

class EstimationDpsForm(forms.Form):
    year = forms.IntegerField(required=True)
    estimation=forms.DecimalField(min_value=0, decimal_places=6, required=True)
    products_id=forms.IntegerField(required=True)
    
class SettingsForm(forms.Form):
    DefaultAmountToInvest= forms.IntegerField(required=True)
    
class ChangeSellingPriceSeveralInvestmentsForm(forms.Form):
    selling_price=forms.DecimalField(min_value=0, decimal_places=6, required=True)
    selling_expiration=forms.DateField(required=False)
    investments=forms.CharField(required=True)
    
