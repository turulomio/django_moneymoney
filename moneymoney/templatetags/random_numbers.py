from random import randint
from django import template

register = template.Library()

@register.simple_tag
def random_integer(a, b):
    return randint(a, b)