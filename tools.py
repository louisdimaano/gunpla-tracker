from forms import read_text, read_checkbox

CATEGORIES = ["Nippers", "Knives", "Sanding", "Scribing", "Panel lining",
              "Top coat", "Glue and cement", "Other"]


def read_tool_form(form):
    """Check the tool form and return (values, errors)."""
    errors = []

    name = read_text(form, "name")
    if not name:
        errors.append("Give the tool a name.")

    category = form.get("category", "")
    if category not in CATEGORIES:
        errors.append("Pick a category from the list.")

    runs_out = read_checkbox(form, "runs_out")
    running_low = read_checkbox(form, "running_low") if runs_out else 0

    values = {
        "name": name,
        "category": category,
        "runs_out": runs_out,
        "running_low": running_low,
        "notes": read_text(form, "notes"),
    }
    return values, errors


def sort_tools(tools):
    """Sort tools by category (in CATEGORIES order), then by name."""

    def sort_key(tool):
        if tool["category"] in CATEGORIES:
            place = CATEGORIES.index(tool["category"])
        else:
            place = len(CATEGORIES)
        return (place, tool["name"].casefold())

    return sorted(tools, key=sort_key)