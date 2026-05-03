import time
from django import template

register = template.Library()

# Module-level cache so every |eucomma call on a page doesn't hit the DB.
# Invalidated after 60 seconds.
_fmt_cache = {'value': None, 'ts': 0.0}
_CACHE_TTL = 60.0


def _get_cached_format():
    """Return the active number format ('de' or 'en'), reading from DB at most once per minute."""
    now = time.monotonic()
    if _fmt_cache['value'] is None or now - _fmt_cache['ts'] > _CACHE_TTL:
        from gui.models import LocalSettings
        obj = LocalSettings.objects.filter(key='GUI-NumberFormat').first()
        if obj is None:
            LocalSettings(key='GUI-NumberFormat', value='de').save()
        _fmt_cache['value'] = obj.value if obj is not None else 'de'
        _fmt_cache['ts'] = now
    return _fmt_cache['value']


@register.filter
def eucomma(value):
    """Format an integer using the configured locale style.

    'de' (default) → European: '.' as thousands separator  (1.000.000)
    'en'           → English:  ',' as thousands separator  (1,000,000)
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return value

    fmt = _get_cached_format()
    formatted = f'{int_value:,}'          # Python always uses ',' here
    if fmt == 'de':
        return formatted.replace(',', '.')
    return formatted                      # 'en': keep Python's comma-thousands


@register.simple_tag
def get_number_format():
    """Template tag that returns the active number-format setting ('de' or 'en').

    Usage in templates::

        {% get_number_format as num_fmt %}
        const NUMBER_FORMAT = "{{ num_fmt }}";
    """
    return _get_cached_format()
