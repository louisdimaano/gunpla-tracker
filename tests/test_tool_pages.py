import db

TOOL = {"name": "GodHand SPN-120", "category": "Nippers", "notes": ""}


def add_tool(client, **changes):
    return client.post("/tools/new", data={**TOOL, **changes})


def only_tool():
    conn = db.get_db()
    row = conn.execute("SELECT * FROM tools").fetchone()
    conn.close()
    return row


def test_empty_tool_list_says_no_tools_yet(client):
    page = client.get("/tools")
    assert page.status_code == 200
    assert b"No tools yet" in page.data
    assert b'href="/tools/new"' in page.data


def test_added_tool_shows_in_list(client):
    assert add_tool(client).status_code == 302
    assert b"GodHand SPN-120" in client.get("/tools").data


def test_blank_name_shows_error(client):
    page = add_tool(client, name="")
    assert b"Give the tool a name." in page.data


def test_search_matches_part_of_name(client):
    add_tool(client)
    add_tool(client, name="Tamiya Extra Thin Cement", category="Glue and cement")
    page = client.get("/tools?q=godhand").data
    assert b"GodHand SPN-120" in page
    assert b"Tamiya Extra Thin Cement" not in page


def test_tools_list_by_category(client):
    add_tool(client, name="Tamiya Extra Thin Cement", category="Glue and cement")
    add_tool(client)
    page = client.get("/tools").data
    assert page.index(b"GodHand SPN-120") < page.index(b"Tamiya Extra Thin Cement")


def test_running_low_only_shows_for_things_that_run_out(client):
    add_tool(client, running_low="on")
    assert b"Running low" not in client.get("/tools").data
    add_tool(client, name="400 grit sandpaper", category="Sanding", runs_out="on", running_low="on")
    assert b"Running low" in client.get("/tools").data


def test_edit_tool_saves_changes(client):
    add_tool(client)
    client.post(f"/tools/{only_tool()['id']}/edit", data={**TOOL, "notes": "Use on thin gates only"})
    assert only_tool()["notes"] == "Use on thin gates only"


def test_delete_removes_tool(client):
    add_tool(client)
    client.post(f"/tools/{only_tool()['id']}/delete")
    assert only_tool() is None


def test_missing_tool_is_not_found(client):
    assert client.get("/tools/999/edit").status_code == 404
    assert client.post("/tools/999/edit", data=TOOL).status_code == 404
    assert client.post("/tools/999/delete").status_code == 404


def test_menu_links_to_tools(client):
    assert b'href="/tools"' in client.get("/").data