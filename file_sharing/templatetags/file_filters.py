import os
from django import template

register = template.Library()


@register.filter(name='basename')
def basename(value):
    """
    Returns the basename of a file path.
    Usage: {{ file.name|basename }}
    """
    if value:
        return os.path.basename(value)
    return value
