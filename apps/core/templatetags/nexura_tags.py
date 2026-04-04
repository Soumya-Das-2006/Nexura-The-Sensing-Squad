"""
apps/core/templatetags/nexura_tags.py

Custom template filters and tags for Nexura.
"""
from django import template

register = template.Library()


@register.filter(name='split')
def split_filter(value, delimiter=','):
    """Split a string by delimiter. Usage: {{ "a,b,c"|split:"," }}"""
    if not value:
        return []
    return str(value).split(delimiter)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get dict item by key. Usage: {{ mydict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='floatformat_inr')
def floatformat_inr(value):
    """Format a number as Indian Rupees."""
    try:
        return f"₹{float(value):,.0f}"
    except (ValueError, TypeError):
        return '₹0'


@register.filter(name='index')
def index_filter(sequence, position):
    """Get item at index. Usage: {{ mylist|index:0 }}"""
    try:
        return sequence[int(position)]
    except (IndexError, ValueError, TypeError):
        return ''


@register.filter(name='startswith')
def startswith_filter(value, prefix):
    """Check if string starts with prefix."""
    return str(value).startswith(str(prefix))


@register.filter(name='endswith')
def endswith_filter(value, suffix):
    """Check if string ends with suffix."""
    return str(value).endswith(str(suffix))


@register.filter(name='split_pairs')
def split_pairs_filter(value, pair_sep=':'):
    """
    Split comma-separated 'key:value' string into list of [key, value] pairs.
    Usage: {% for k, v in "a:A,b:B"|split_pairs:":" %}
    """
    if not value:
        return []
    result = []
    for item in str(value).split(','):
        parts = item.split(pair_sep, 1)
        if len(parts) == 2:
            result.append(parts)
        else:
            result.append([item, item])
    return result
