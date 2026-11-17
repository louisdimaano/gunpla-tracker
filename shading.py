"""Shading mixer: lighter and darker versions of a paint, with mixing ratios.

Colors are mixed with Mixbox, which imitates real pigment instead of screen light.
"""
import mixbox

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# (parts of base paint, parts of white or black), from a touch to a lot
LIGHTER = [(10, 1), (5, 1), (3, 1), (2, 1), (1, 1), (1, 2), (1, 3)]
DARKER = [(20, 1), (10, 1), (5, 1), (3, 1), (2, 1), (1, 1)]


def hex_to_rgb(color):
    """'#1d4e9e' -> (29, 78, 158)"""
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(rgb):
    """(29, 78, 158) -> '#1d4e9e'"""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def parts(count, name):
    """3, 'base' -> '3 parts base'; 1, 'white' -> '1 part white'"""
    word = "part" if count == 1 else "parts"
    return f"{count} {word} {name}"


def mix(base_color, partner, base_parts, partner_parts):
    """Mix two colors by parts and return the result as #rrggbb."""
    amount = partner_parts / (base_parts + partner_parts)
    return rgb_to_hex(mixbox.lerp(hex_to_rgb(base_color), partner, amount))


def shade_steps(base_color):
    """Every slider stop, darkest first: the darker mixes, the paint itself, then the lighter mixes."""
    darker = [
        {"color": mix(base_color, BLACK, b, p), "label": f"{parts(b, 'base')} : {parts(p, 'black')}"}
        for b, p in DARKER
    ]
    lighter = [
        {"color": mix(base_color, WHITE, b, p), "label": f"{parts(b, 'base')} : {parts(p, 'white')}"}
        for b, p in LIGHTER
    ]
    original = {"color": base_color, "label": "Straight from the jar"}
    return list(reversed(darker)) + [original] + lighter