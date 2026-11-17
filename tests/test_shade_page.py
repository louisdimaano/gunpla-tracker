import db

PAINT = {"name": "Gundam Blue", "brand": "Mr. Color", "code": "C-5", "color": "#1d4e9e",
         "quantity": "1", "notes": ""}


def add_paint(client):
    client.post("/paints/new", data=PAINT)
    conn = db.get_db()
    paint_id = conn.execute("SELECT id FROM paints").fetchone()["id"]
    conn.close()
    return paint_id


def test_shade_page_shows_every_mix(client):
    paint_id = add_paint(client)
    page = client.get(f"/paints/{paint_id}/shade")
    assert page.status_code == 200
    assert b"Shade Gundam Blue" in page.data
    assert b"Straight from the jar" in page.data
    assert b"10 parts base : 1 part white" in page.data
    assert b"20 parts base : 1 part black" in page.data


def test_paint_card_links_to_shade_page(client):
    paint_id = add_paint(client)
    assert f'href="/paints/{paint_id}/shade"'.encode() in client.get("/paints").data


def test_shade_page_for_missing_paint_is_not_found(client):
    assert client.get("/paints/999/shade").status_code == 404