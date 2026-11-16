from datetime import date

import db

FORM = {"name": "Gundam Exia", "grade": "HG", "series": "HG Gundam 00", "kit_number": "",
        "status": "Not Started", "difficulty": "", "build_quality": "", "finished_on": "", "notes": ""}


def add_kit(client, **changes):
    return client.post("/kits/new", data={**FORM, **changes})


def test_empty_list_says_no_kits_yet(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"No kits yet" in page.data
    assert b'href="/kits/new"' in page.data


def test_added_kit_shows_in_list(client):
    response = add_kit(client)
    assert response.status_code == 302
    assert b"Gundam Exia" in client.get("/").data


def test_bad_kit_number_shows_error_and_keeps_input(client):
    page = add_kit(client, kit_number="15a")
    assert page.status_code == 200
    assert b"Kit number must be a whole number above 0." in page.data
    assert b'value="Gundam Exia"' in page.data
    assert b"No kits yet" in client.get("/").data


def only_kit():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM kits").fetchone()
    conn.close()
    return row


def test_edit_built_to_painted_moves_date_to_today(client):
    add_kit(client, status="Built", finished_on="2026-01-10")
    kit_id = only_kit()["id"]
    client.post(f"/kits/{kit_id}/edit", data={**FORM, "status": "Painted", "finished_on": "2026-01-10"})
    assert only_kit()["status"] == "Painted"
    assert only_kit()["finished_on"] == date.today().isoformat()


def test_edit_form_shows_saved_values(client):
    add_kit(client, notes="Falls apart")
    page = client.get(f"/kits/{only_kit()['id']}/edit")
    assert b"Falls apart" in page.data


def test_delete_removes_kit(client):
    add_kit(client)
    client.post(f"/kits/{only_kit()['id']}/delete")
    assert only_kit() is None


def test_missing_kit_is_not_found(client):
    assert client.get("/kits/999/edit").status_code == 404
    assert client.post("/kits/999/edit", data=FORM).status_code == 404
    assert client.post("/kits/999/delete").status_code == 404