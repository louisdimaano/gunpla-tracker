from shading import hex_to_rgb, rgb_to_hex, parts, mix, shade_steps, WHITE, BLACK, LIGHTER, DARKER

BLUE = "#1d4e9e"


def brightness(color):
    r, g, b = hex_to_rgb(color)
    return r + g + b


def test_hex_and_rgb_convert_both_ways():
    assert hex_to_rgb(BLUE) == (29, 78, 158)
    assert rgb_to_hex((29, 78, 158)) == BLUE


def test_parts_uses_singular_for_one():
    assert parts(1, "white") == "1 part white"
    assert parts(3, "base") == "3 parts base"


def test_mixing_with_white_is_lighter_and_black_is_darker():
    assert brightness(mix(BLUE, WHITE, 2, 1)) > brightness(BLUE)
    assert brightness(mix(BLUE, BLACK, 2, 1)) < brightness(BLUE)


def test_steps_have_the_paint_itself_in_the_middle():
    steps = shade_steps(BLUE)
    assert len(steps) == len(DARKER) + 1 + len(LIGHTER)
    middle = steps[len(DARKER)]
    assert middle == {"color": BLUE, "label": "Straight from the jar"}


def test_steps_go_from_darkest_to_lightest():
    values = [brightness(step["color"]) for step in shade_steps(BLUE)]
    assert values == sorted(values)


def test_step_labels():
    steps = shade_steps(BLUE)
    assert steps[0]["label"] == "1 part base : 1 part black"
    assert steps[len(DARKER) - 1]["label"] == "20 parts base : 1 part black"
    assert steps[len(DARKER) + 1]["label"] == "10 parts base : 1 part white"
    assert steps[-1]["label"] == "1 part base : 3 parts white"


def test_works_for_white_and_black_paints():
    for color in ("#ffffff", "#000000"):
        steps = shade_steps(color)
        assert all(step["color"].startswith("#") and len(step["color"]) == 7 for step in steps)