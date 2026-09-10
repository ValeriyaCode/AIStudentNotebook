from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key, '')
    return ''


@register.filter
def is_selected(value, option):
    return option in value if isinstance(value, list) else False
