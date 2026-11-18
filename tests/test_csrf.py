import re

from app import app

KIT = {"name": "Gundam Exia", "grade": "HG", "series": "", "kit_number": "",
       "status": "Not Started", "difficulty": "", "build_quality": "", "finished_on": "", "notes": ""}
PAINT = {"name": "Gundam Blue", "brand": "", "code": "", "color": "#1d4e9e", "quantity": "1", "notes": ""}
TOOL = {"name": "GodHand SPN-120", "category": "Nippers", "notes": ""}


def token_on(page):
    return re.search(r'name="csrf_token" value="([^"]+)"', page.data.decode()).group(1)


def turn_on_csrf(monkeypatch):
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)


def test_form_without_its_token_is_rejected(client, monkeypatch):
    turn_on_csrf(monkeypatch)
    response = client.post("/kits/new", data=KIT)
    assert response.status_code == 400
    assert b"nothing was changed" in response.data
    assert b"Gundam Exia" not in client.get("/").data


def test_form_with_its_token_works(client, monkeypatch):
    turn_on_csrf(monkeypatch)
    token = token_on(client.get("/kits/new"))
    response = client.post("/kits/new", data={**KIT, "csrf_token": token})
    assert response.status_code == 302


def test_a_made_up_token_is_rejected(client, monkeypatch):
    turn_on_csrf(monkeypatch)
    response = client.post("/kits/new", data={**KIT, "csrf_token": "made-up"})
    assert response.status_code == 400


def test_every_form_carries_a_token(client, monkeypatch):
    client.post("/kits/new", data=KIT)
    client.post("/paints/new", data=PAINT)
    client.post("/tools/new", data=TOOL)
    turn_on_csrf(monkeypatch)
    pages = ["/", "/kits/new", "/kits/1/edit", "/paints", "/paints/new", "/paints/1/edit",
             "/paints/1/shade", "/tools", "/tools/new", "/tools/1/edit", "/account"]
    for path in pages:
        html = client.get(path).data.decode()
        assert html.count('method="post"') == html.count('name="csrf_token"'), path


def test_login_and_forgot_forms_carry_a_token(anon_client, monkeypatch):
    anon_client.post("/setup", data={"password": "zaku-ii-kai", "confirm": "zaku-ii-kai"})
    anon_client.post("/logout")
    turn_on_csrf(monkeypatch)
    for path in ("/login", "/forgot"):
        assert 'name="csrf_token"' in anon_client.get(path).data.decode(), path


def test_tokens_last_as_long_as_the_login():
    assert app.config["WTF_CSRF_TIME_LIMIT"] is None

def forms_on(html):
    """Every POST form on a page, from its opening tag to </form>."""
    return re.findall(r'<form method="post".*?</form>', html, re.DOTALL)


def test_every_token_is_inside_its_form(anon_client, monkeypatch):
    anon_client.post("/setup", data={"password": "zaku-ii-kai", "confirm": "zaku-ii-kai"})
    anon_client.post("/kits/new", data=KIT)
    anon_client.post("/paints/new", data=PAINT)
    anon_client.post("/tools/new", data=TOOL)
    anon_client.post("/logout")
    turn_on_csrf(monkeypatch)
    for path in ("/login", "/forgot"):
        forms = forms_on(anon_client.get(path).data.decode())
        assert forms, path
        for form in forms:
            assert 'name="csrf_token"' in form, path

    with anon_client.session_transaction() as session:
        session["logged_in"] = True
    pages = ["/", "/kits/new", "/kits/1/edit", "/paints", "/paints/new", "/paints/1/edit",
             "/tools", "/tools/new", "/tools/1/edit", "/account"]
    for path in pages:
        forms = forms_on(anon_client.get(path).data.decode())
        assert forms, path
        for form in forms:
            assert 'name="csrf_token"' in form, path