from tools import read_tool_form, sort_tools


def good_tool(**changes):
    form = {"name": "GodHand SPN-120", "category": "Nippers", "notes": ""}
    form.update(changes)
    return form


def test_valid_tool_form_has_no_errors():
    values, errors = read_tool_form(good_tool())
    assert errors == []
    assert values["name"] == "GodHand SPN-120"
    assert values["runs_out"] == 0
    assert values["notes"] is None


def test_blank_tool_name_is_rejected():
    _, errors = read_tool_form(good_tool(name=""))
    assert errors == ["Give the tool a name."]


def test_unknown_category_is_rejected():
    _, errors = read_tool_form(good_tool(category="Lightsaber"))
    assert errors == ["Pick a category from the list."]


def test_running_low_needs_runs_out():
    values, _ = read_tool_form(good_tool(running_low="on"))
    assert values["running_low"] == 0
    values, _ = read_tool_form(good_tool(runs_out="on", running_low="on"))
    assert values["running_low"] == 1


def test_tools_sort_by_category_then_name():
    tools = [{"name": "Tamiya Cement", "category": "Glue and cement"},
             {"name": "sanding stick", "category": "Sanding"},
             {"name": "GodHand", "category": "Nippers"},
             {"name": "Art knife", "category": "Knives"},
             {"name": "Alpha nippers", "category": "Nippers"}]
    assert [t["name"] for t in sort_tools(tools)] == [
        "Alpha nippers", "GodHand", "Art knife", "sanding stick", "Tamiya Cement"]