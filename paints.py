import re

from forms import read_number, read_text, read_checkbox

DEFAULT_COLOR = "#808080"
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def read_paint_form(form):
    """Check the paint form and return (values, errors)."""
    errors = []

    name = read_text(form, "name")
    if not name:
        errors.append("Give the paint a name.")

    quantity, ok = read_number(form.get("quantity", ""), lowest=0)
    if not ok:
        errors.append("Quantity must be a whole number, 0 or more.")
    elif quantity is None:
        quantity = 1

    color = form.get("color", "").strip()
    if not HEX_COLOR.fullmatch(color):
        errors.append("Pick a color with the color picker.")
        color = DEFAULT_COLOR

    values = {
        "name": name,
        "brand": read_text(form, "brand"),
        "code": read_text(form, "code"),
        "color": color.lower(),
        "quantity": quantity,
        "running_low": read_checkbox(form, "running_low"),
        "notes": read_text(form, "notes"),
    }
    return values, errors


def change_quantity(quantity, change):
    """Add or remove jars, never going below 0."""
    return max(0, quantity + change)