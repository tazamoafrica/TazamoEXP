from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(field, css_class):
    """Adds a CSS class to the specified form field."""
    return field.as_widget(attrs={'class': css_class})

@register.filter
def divided_by(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0