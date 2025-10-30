"""Custom template filters for assessment templates."""
from django import template

register = template.Library()


@register.filter
def humanize_signal(value: str) -> str:
    """Turn snake_case signal labels into readable phrases."""
    if not isinstance(value, str):
        return value
    cleaned = value.replace("_", " ").strip()
    if not cleaned:
        return ""
    return cleaned.title() if value.islower() else cleaned
