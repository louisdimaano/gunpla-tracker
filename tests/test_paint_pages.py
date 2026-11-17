import db

PAINT = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5", "color": "#1d4e9e",
         "quantity": "1", "notes": ""}


def add_paint(client, **changes):
    return client.post("/paints/new", data={**PAINT, **changes})


def only_paint():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM paints").fetchone()
    conn.close()
    return row


def test_empty_paint_list_says_no_paints_yet(client):
    page = client.get("/paints")
    assert page.status_code == 200
    assert b"No paints yet" in page.data
    assert b'href="/paints/new"' in page.data


def test_added_paint_shows_in_list(client):
    assert add_paint(client).status_code == 302
    assert b"Gundam Blue" in client.get("/paints").data


def test_bad_color_shows_error_and_keeps_input(client):
    page = add_paint(client, color="blue")
    assert b"Pick a color with the color picker." in page.data
    assert b'value="Gundam Blue"' in page.data


def test_search_matches_name_or_code(client):
    add_paint(client)
    add_paint(client, name="Titanium Gold", code="XF-1")
    page = client.get("/paints?q=c-5").data
    assert b"Gundam Blue" in page
    assert b"Titanium Gold" not in page
    page = client.get("/paints?q=gold").data
    assert b"Titanium Gold" in page
    assert b"Gundam Blue" not in page


def test_search_with_no_match_says_so(client):
    add_paint(client)
    assert b"No paints match" in client.get("/paints?q=purple").data


def test_used_up_paint_is_hidden_until_asked_for(client):
    add_paint(client, name="Empty Red", quantity="0")
    add_paint(client)
    assert b"Empty Red" not in client.get("/paints").data
    assert b"Empty Red" not in client.get("/paints?q=red").data
    assert b"Empty Red" in client.get("/paints?used_up=1").data


def test_paint_form_suggests_existing_brands(client):
    add_paint(client)
    assert b'<option value="Mr. Color">' in client.get("/paints/new").data


def test_menu_links_to_paints(client):
    assert b'href="/paints"' in client.get("/").data