## @package admin
## @brief Defines everything for Django Admin Site

## Se mete en books  porque necesita los modelos


from django.utils.translation import ugettext_lazy as _
from moneymoney.models import Banks, Accountsoperations
from django.contrib.auth.models import User, Group
from django.urls import reverse_lazy
from django.contrib import admin# Need to import this since auth models get registered on import.


class BankAdmin(admin.ModelAdmin):
    model = Banks
    ordering = ['name']
    list_display = ['name','active']
    search_fields = ['name', 'active']
    list_filter = ('active', )
class AccountoperationAdmin(admin.ModelAdmin):
    model = Accountsoperations
    list_display = ['datetime','comment']


admin.site.site_title = _('Django moneymoney')
admin.site.site_header = _('Django moneymoney')
admin.site.index_title = _('My Django moneymoney administration')

admin.site.register(Accountsoperations)
admin.site.register(Banks)
    
admin.site.site_url = reverse_lazy('home') 
admin.site.logout_template=reverse_lazy('home')

admin.site.unregister(User)
admin.site.unregister(Group)
