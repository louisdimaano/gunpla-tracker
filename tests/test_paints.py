from paints import read_paint_form, change_quantity


def good_paint(**changes):
    form = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5",
            "color": "#1D4E9E", "quantity": "2", "notes": ""}
    form.update(changes)
    return form


def test_valid_paint_form_has_no_errors():
    values, errors = read_paint_form(good_paint())
    assert errors == []
    assert values["name"] == "Gundam Blue"
    assert values["code"] == "C-5"
    assert values["color"] == "#1d4e9e"
    assert values["quantity"] == 2
    assert values["running_low"] == 0
    assert values["notes"] is None


def test_blank_paint_name_is_rejected():
    _, errors = read_paint_form(good_paint(name=" "))
    assert errors == ["Give the paint a name."]


def test_blank_quantity_means_one():
    values, errors = read_paint_form(good_paint(quantity=""))
    assert errors == []
    assert values["quantity"] == 1


def test_zero_quantity_is_allowed():
    values, errors = read_paint_form(good_paint(quantity="0"))
    assert errors == []
    assert values["quantity"] == 0


def test_bad_quantity_is_rejected():
    for bad in ("-1", "two", "1.5"):
        _, errors = read_paint_form(good_paint(quantity=bad))
        assert errors == ["Quantity must be a whole number, 0 or more."]


def test_bad_color_is_rejected():
    for bad in ("blue", "#12345", "#12345g", ""):
        _, errors = read_paint_form(good_paint(color=bad))
        assert errors == ["Pick a color with the color picker."]


def test_running_low_checkbox():
    values, _ = read_paint_form(good_paint(running_low="on"))
    assert values["running_low"] == 1


def test_quantity_never_goes_below_zero():
    assert change_quantity(2, 1) == 3
    assert change_quantity(1, -1) == 0
    assert change_quantity(0, -1) == 0