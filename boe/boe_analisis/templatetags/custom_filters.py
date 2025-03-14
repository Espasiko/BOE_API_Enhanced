"""
Filtros personalizados para las plantillas
"""
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def multiply(value, arg):
    """
    Multiplica el valor por el argumento
    Uso: {{ value|multiply:100 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value
