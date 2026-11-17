"""Small helpers for reading web form fields. Shared by kits, paints, and tools."""


def read_number(text, lowest, highest=None):
    """Turn form text into a whole number.

    Returns (number, ok). An empty box gives (None, True).
    """
    text = text.strip()
    if not text:
        return None, True
    if not text.isdecimal():
        return None, False
    number = int(text)
    if number < lowest or (highest is not None and number > highest):
        return None, False
    return number, True


def read_text(form, field):
    """Read a text box. Extra spaces are trimmed, and an empty box gives None."""
    return form.get(field, "").strip() or None


def read_checkbox(form, field):
    """Read a checkbox as 1 (ticked) or 0 (not ticked)."""
    return 1 if field in form else 0