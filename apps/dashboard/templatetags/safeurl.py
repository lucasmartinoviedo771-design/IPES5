from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.simple_tag
def safe_url(name, *args, **kwargs):
    """
    Igual que {% url %} pero si no existe la ruta, devuelve '#'
    en vez de romper con 500.
    Uso: <a href="{% safe_url 'pre_pdf' obj.pk %}">PDF</a>
    """
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"
