## THIS IS FILE IS FROM https://github.com/turulomio/reusingcode IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT
## DO NOT UPDATE IT IN YOUR CODE IT WILL BE REPLACED USING FUNCTION IN README

#    Esta clase la cree después de probar la app django-sitemaps, tenía cosas buenas, tree, breadcumb, title
#    Era muy complicada y luego me liaba cuando el menu necesitaba parámetros

#    You need to create a menu in app.context_processor.py


from django import template

register = template.Library()
## {% load listdicttags %}
## You can use it so:{{list_ioc_better|sum:'gains_net_user'}}
@register.filter(name='sum')
def sum(listdict, key):
    r=0
    for d in listdict:
        r=r+d[key]
    return r
