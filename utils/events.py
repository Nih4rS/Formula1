from __future__ import annotations
import unicodedata

EVENT_NAME_OVERRIDES = {
    "sao-paulo-grand-prix": "Sao Paulo Grand Prix",
    "mexico-city-grand-prix": "Mexico City Grand Prix",
    "las-vegas-grand-prix": "Las Vegas Grand Prix",
    "emilia-romagna-grand-prix": "Emilia Romagna Grand Prix",
}


def slug_to_event_name(slug: str) -> str:
    """Convert folder-style slug to FastF1's expected event name."""
    slug_norm = slug.replace("_", "-").lower()
    if slug_norm in EVENT_NAME_OVERRIDES:
        return EVENT_NAME_OVERRIDES[slug_norm]
    return " ".join(part.capitalize() for part in slug_norm.split("-"))


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def event_name_to_slug(name: str) -> str:
    """Convert FastF1 event display name into a filesystem-safe slug.

    - Lowercase
    - Replace spaces with '-'
    - Strip accents (e.g., São -> Sao)
    """
    name_ascii = _strip_accents(name)
    return name_ascii.lower().replace(" ", "-")
