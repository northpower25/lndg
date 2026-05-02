from django import template

register = template.Library()


@register.filter
def eucomma(value):
    """Format a number using European style: '.' as thousands separator, ',' as decimal separator.
    Example: 1000000 -> '1.000.000'
    """
    try:
        int_value = int(value)
        # Format with commas (US style), then swap: comma -> dot
        return f'{int_value:,}'.replace(',', '.')
    except (ValueError, TypeError):
        return value
