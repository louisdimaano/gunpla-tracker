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