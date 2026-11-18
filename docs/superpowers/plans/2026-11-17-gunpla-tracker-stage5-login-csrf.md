# Gunpla Tracker Stage 5 (Login, Recovery Code, and CSRF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For this project specifically:** Louis builds it himself on his Windows PC, guided step by step, with every piece of code explained in plain terms before he types it. The same pattern goes into SpoolManager afterward.

**Goal:** Every page needs a login, a forgotten password can be reset with a one-time recovery code, the password can be changed while logged in, and every form is protected against cross-site request forgery (CSRF).

**Architecture:** One account with one password. The first visit shows a "Set a password" page; it saves the password and a random recovery code, both only as hashes, in a new `users` table, and shows the recovery code once. Logging in puts `logged_in` in Flask's signed session cookie for 30 days. A `before_request` check sends anyone without it to the login page (or to setup, if no password exists yet), so no route can be forgotten. "Forgot password?" takes the recovery code and a new password, then shows a fresh code. A Password page changes the password after checking the current one. Flask-WTF's `CSRFProtect` checks a hidden token on every POST.

**Tech Stack:** Flask sessions, `werkzeug.security` (comes with Flask), `secrets` (Python's built-in random codes), `Flask-WTF==1.3.0`, pytest.

## Global Constraints

- One account, password only (no username); at least 8 characters, typed twice
- Only hashes are stored (`generate_password_hash` / `check_password_hash`), for both the password and the recovery code
- Recovery code: 4 groups of 4 characters from `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (no 0/O or 1/I/L), shown once; case, spaces, and dashes don't matter when typing it; using it gives a new one (Louis's choice, Nov 17, 2026)
- Change password asks for the current password and keeps the recovery code (Louis's choice)
- The setup page works only while no password exists; after that it sends you to login
- Logged in for 30 days per device (`PERMANENT_SESSION_LIFETIME`), cookie `SameSite=Lax`; Log out is a POST button in the menu
- `SECRET_KEY` from `.env`; if it's missing, a random key is made at startup (sessions then end on restart, but can't be forged). The old fixed fallback key is removed.
- Every POST form carries `csrf_token`; tokens last as long as the login (`WTF_CSRF_TIME_LIMIT = None`)
- Last resort if both the password and the code are lost: delete the `users` row on the server, and the setup page comes back
- Not in this stage: email resets, rate limiting, more than one account, HTTPS

## Review Focus

1. **A page left unprotected.** Protection is one `before_request` check for every page; only login, setup, forgot, and static files are let through. Pinned in Task 2.
2. **Setup or reset used to take over the account.** `/setup` refuses once a password exists; `/forgot` needs the right code, and a code works once. Pinned in Tasks 2 and 3.
3. **A form missed when adding tokens.** One test opens every page with a form and checks each `method="post"` has a token. Pinned in Task 4.
4. **A token expiring on an open tab.** Flask-WTF tokens expire after an hour by default, so tapping +1 on a Paints tab left open all afternoon would fail. Turned off; pinned in Task 4.
5. **Error text with an apostrophe.** Jinja writes `'` as `&#39;`, so a test looking for "didn't" never finds it. Error messages are worded without apostrophes ("Wrong recovery code."). Task 3.

---

### Task 1: Password and recovery code rules, and logged-in tests

**Files:** create `auth.py`, `tests/test_auth.py`; replace `tests/conftest.py`

**Interfaces:**
- Produces: `MIN_LENGTH = 8`, `CODE_LETTERS`; `read_new_password(form) -> (password, errors)`; `new_recovery_code() -> str`; `normalize_code(text) -> str`; fixtures `anon_client` (logged out, empty database, CSRF off) and `client` (same, logged in)

- [ ] **Step 1: Failing tests** (`tests/test_auth.py`)

```python
import re

from auth import read_new_password, new_recovery_code, normalize_code


def test_matching_long_password_is_accepted():
    password, errors = read_new_password({"password": "zaku-ii-kai", "confirm": "zaku-ii-kai"})
    assert errors == []
    assert password == "zaku-ii-kai"


def test_short_password_is_rejected():
    _, errors = read_new_password({"password": "exia", "confirm": "exia"})
    assert errors == ["Use at least 8 characters."]


def test_mismatched_passwords_are_rejected():
    _, errors = read_new_password({"password": "zaku-ii-kai", "confirm": "zaku-ii-kia"})
    assert errors == ["The two passwords don't match."]


def test_spaces_count_and_are_kept():
    password, errors = read_new_password({"password": " my kit ", "confirm": " my kit "})
    assert errors == []
    assert password == " my kit "


def test_recovery_code_looks_right():
    code = new_recovery_code()
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", code)
    assert not set("01OIL") & set(code)


def test_recovery_codes_are_different_each_time():
    assert new_recovery_code() != new_recovery_code()


def test_normalize_code_ignores_case_spaces_and_dashes():
    assert normalize_code(" 7kq4 m2xd-9plr f6tw ") == "7KQ4M2XD9PLRF6TW"
    assert normalize_code("7KQ4-M2XD-9PLR-F6TW") == "7KQ4M2XD9PLRF6TW"
```

- [ ] **Step 2:** Run, expect `No module named 'auth'`
- [ ] **Step 3:** Write `auth.py` (passwords are never trimmed, unlike other form fields; codes use `secrets.choice`). Replace `conftest.py`:

```python
import os
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "import.db"))

import pytest
import db
from app import app


@pytest.fixture
def anon_client(tmp_path, monkeypatch):
    """A browser that isn't logged in, with an empty database."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", False)
    return app.test_client()


@pytest.fixture
def client(anon_client):
    """A browser that is already logged in."""
    with anon_client.session_transaction() as session:
        session["logged_in"] = True
    return anon_client
```

- [ ] **Step 4:** `pytest`, expect 94 passed. Commit: "Add password and recovery code rules"

### Task 2: Setup, login, logout, and the login gate

**Files:** modify `schema.sql`, `app.py`, `templates/base.html`, `static/style.css`; create `templates/setup.html`, `templates/recovery_code.html`, `templates/login.html`, `tests/test_login_pages.py`

**Interfaces:**
- Produces: `saved_user() -> Row | None`, `save_password(password, new_account=False) -> str` (the new recovery code), `log_in()`, `require_login()` (`before_request`), routes `setup`, `login`, `logout` (POST only)

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL,
    recovery_hash TEXT NOT NULL
);
```

- [ ] **Step 1: Failing tests** (`tests/test_login_pages.py`)

```python
from werkzeug.security import check_password_hash

import db

PASSWORD = "zaku-ii-kai"
KIT = {"name": "Gundam Exia", "grade": "HG", "series": "", "kit_number": "",
       "status": "Not Started", "difficulty": "", "build_quality": "", "finished_on": "", "notes": ""}


def set_password(anon_client, password=PASSWORD):
    return anon_client.post("/setup", data={"password": password, "confirm": password})


def saved_user():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM users").fetchone()
    conn.close()
    return row


def count_kits():
    conn = db.get_db()
    count = conn.execute("SELECT COUNT(*) FROM kits").fetchone()[0]
    conn.close()
    return count


def test_first_visit_goes_to_setup(anon_client):
    response = anon_client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/setup")


def test_setup_saves_only_a_hash(anon_client):
    set_password(anon_client)
    saved = saved_user()["password_hash"]
    assert PASSWORD not in saved
    assert check_password_hash(saved, PASSWORD)


def test_setup_logs_you_in(anon_client):
    set_password(anon_client)
    assert anon_client.get("/").status_code == 200


def test_setup_shows_errors_and_saves_nothing(anon_client):
    page = anon_client.post("/setup", data={"password": "exia", "confirm": "exia"})
    assert b"Use at least 8 characters." in page.data
    assert saved_user() is None


def test_setup_closes_once_a_password_exists(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    response = anon_client.post("/setup", data={"password": "new-password", "confirm": "new-password"})
    assert response.headers["Location"].endswith("/login")
    assert check_password_hash(saved_user()["password_hash"], PASSWORD)


def test_logged_out_visitor_is_sent_to_login(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    for path in ("/", "/paints", "/tools", "/kits/new", "/kits/1/edit"):
        response = anon_client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_logged_out_visitor_cannot_change_anything(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    anon_client.post("/kits/new", data=KIT)
    assert count_kits() == 0


def test_wrong_password_is_rejected(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    page = anon_client.post("/login", data={"password": "wrong-password"})
    assert b"Wrong password." in page.data
    assert anon_client.get("/").status_code == 302


def test_right_password_logs_in_for_30_days(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    response = anon_client.post("/login", data={"password": PASSWORD})
    assert response.headers["Location"].endswith("/")
    assert "Expires=" in response.headers["Set-Cookie"]
    assert anon_client.get("/").status_code == 200


def test_styles_load_when_logged_out(anon_client):
    assert anon_client.get("/static/style.css").status_code == 200


def test_menu_shows_log_out_only_when_logged_in(anon_client):
    set_password(anon_client)
    assert b"Log out" in anon_client.get("/").data
    anon_client.post("/logout")
    assert b"Log out" not in anon_client.get("/login").data
```

- [ ] **Step 2:** Run, expect 10 of these 11 to fail (the styles test already passes, since static files have always loaded)
- [ ] **Step 3:** Add the table, the session settings, the random-key fallback, the routes and `before_request` (`OPEN_PAGES` already lists `forgot` for Task 3), the templates (`autocomplete="new-password"` / `"current-password"` so password managers work; setup ends on the recovery code page), and the Log out button (the menu only shows when logged in; it wraps on narrow phones)
- [ ] **Step 4:** `pytest`, expect 105 passed; try it in the browser. Commit: "Add login, setup, and logout"

### Task 3: Forgot password and change password

**Files:** modify `app.py`, `templates/login.html` (a "Forgot password?" link), `templates/base.html` (a Password link), `static/style.css`; create `templates/forgot.html`, `templates/account.html`, `tests/test_recovery_pages.py`

**Interfaces:**
- Consumes: `save_password`, `saved_user`, `log_in` (Task 2); `normalize_code`, `read_new_password` (Task 1)
- Produces: routes `forgot` (`/forgot`, open to logged-out visitors) and `account` (`/account`, logged in)

- [ ] **Step 1: Failing tests** (`tests/test_recovery_pages.py`)

```python
import re

from werkzeug.security import check_password_hash

import db

PASSWORD = "zaku-ii-kai"
NEW_PASSWORD = "gouf-custom"


def code_on(page):
    return re.search(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", page.data.decode()).group(0)


def set_password(anon_client):
    """Set the first password and return the recovery code shown."""
    page = anon_client.post("/setup", data={"password": PASSWORD, "confirm": PASSWORD})
    return code_on(page)


def saved_user():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM users").fetchone()
    conn.close()
    return row


def can_log_in(anon_client, password):
    anon_client.post("/logout")
    response = anon_client.post("/login", data={"password": password})
    return response.status_code == 302


def reset(anon_client, code, password=NEW_PASSWORD):
    anon_client.post("/logout")
    return anon_client.post("/forgot", data={"code": code, "password": password, "confirm": password})


def test_setup_shows_a_recovery_code_and_saves_only_its_hash(anon_client):
    code = set_password(anon_client)
    saved = saved_user()["recovery_hash"]
    assert code.replace("-", "") not in saved
    assert check_password_hash(saved, code.replace("-", ""))


def test_login_page_links_to_forgot_password(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    assert b'href="/forgot"' in anon_client.get("/login").data
    assert anon_client.get("/forgot").status_code == 200


def test_right_code_sets_a_new_password_and_a_new_code(anon_client):
    code = set_password(anon_client)
    page = reset(anon_client, code)
    new_code = code_on(page)
    assert new_code != code
    assert can_log_in(anon_client, NEW_PASSWORD)
    assert not can_log_in(anon_client, PASSWORD)


def test_a_used_code_stops_working(anon_client):
    code = set_password(anon_client)
    reset(anon_client, code)
    page = reset(anon_client, code, password="another-password")
    assert b"Wrong recovery code." in page.data
    assert can_log_in(anon_client, NEW_PASSWORD)


def test_code_can_be_typed_lowercase_without_dashes(anon_client):
    code = set_password(anon_client)
    reset(anon_client, code.lower().replace("-", " "))
    assert can_log_in(anon_client, NEW_PASSWORD)


def test_wrong_code_changes_nothing(anon_client):
    set_password(anon_client)
    page = reset(anon_client, "AAAA-BBBB-CCCC-DDDD")
    assert b"Wrong recovery code." in page.data
    assert can_log_in(anon_client, PASSWORD)


def test_reset_with_short_password_changes_nothing(anon_client):
    code = set_password(anon_client)
    page = reset(anon_client, code, password="exia")
    assert b"Use at least 8 characters." in page.data
    assert can_log_in(anon_client, PASSWORD)


def test_change_password_needs_the_current_one(anon_client):
    set_password(anon_client)
    page = anon_client.post("/account", data={"current": "wrong-password",
                                              "password": NEW_PASSWORD, "confirm": NEW_PASSWORD})
    assert b"Your current password is wrong." in page.data
    assert can_log_in(anon_client, PASSWORD)


def test_change_password_works_and_keeps_the_recovery_code(anon_client):
    code = set_password(anon_client)
    page = anon_client.post("/account", data={"current": PASSWORD,
                                              "password": NEW_PASSWORD, "confirm": NEW_PASSWORD})
    assert b"Password changed." in page.data
    assert can_log_in(anon_client, NEW_PASSWORD)
    reset(anon_client, code, password="third-password")
    assert can_log_in(anon_client, "third-password")


def test_change_password_page_needs_login(anon_client):
    set_password(anon_client)
    anon_client.post("/logout")
    response = anon_client.get("/account")
    assert response.headers["Location"].endswith("/login")
```

- [ ] **Step 2:** Run, expect 8 failed, 2 passed (setup already shows a code from Task 2, and `/account` already sends logged-out visitors to login, like every page)
- [ ] **Step 3:** `forgot` checks the code first, then the new password, then saves both with `save_password` (which makes the new code), logs in, and shows the new code. `account` checks the current password, then the new one, and updates only `password_hash`.
- [ ] **Step 4:** `pytest`, expect 115 passed. Commit: "Add forgot password and change password"

### Task 4: CSRF protection

**Files:** modify `requirements.txt` (`Flask-WTF==1.3.0`), `app.py`, every template with a POST form; create `templates/csrf_error.html`, `tests/test_csrf.py`

- [ ] **Step 1: Failing tests** (`tests/test_csrf.py`)

```python
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
```

- [ ] **Step 2:** `pip install -r requirements-dev.txt`, run, expect these 6 to fail
- [ ] **Step 3:** `CSRFProtect(app)`, `WTF_CSRF_TIME_LIMIT = None`, a `CSRFError` handler showing `csrf_error.html` with status 400, and `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` right after every `<form method="post" ...>` tag (12 forms in 9 templates)
- [ ] **Step 4:** `pytest`, expect 121 passed. Commit: "Protect every form against CSRF"

### Task 5: README and deploy

- [ ] **Step 1:** README: Features (login, recovery code, change password, CSRF), Built With (Flask-WTF), the "no login" note replaced with how login and recovery work, What I Learned, Roadmap. Commit and push.
- [ ] **Step 2:** On the server: `git pull`, `docker compose up -d --build`, then **right away** open `http://homelab:5001`, set the password, and save the recovery code in the password manager (until the password is set, anyone on the tailnet could set it). Log in on the phone too.
- [ ] **Step 3:** Check the Uptime Kuma monitor and the Homepage tile still show green (the home page now redirects to login), and add a change log entry to Homelab Notes, including the last-resort reset:
  `docker compose exec gunpla-tracker python -c "import db; c = db.get_db(); c.execute('DELETE FROM users'); c.commit()"`
