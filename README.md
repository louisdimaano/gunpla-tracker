# Gunpla Tracker

A web app I'm building to keep track of everything on my Gunpla bench: the kits I own and how far along each build is, plus my paints and tools. I can search it from my phone, like when I'm in a hobby store and can't remember if I already have a kit or a paint.

It uses the same stack as my [SpoolManager](https://github.com/louisdimaano/spool-manager) project.

It runs in Docker on my home server, so I can check it from my phone anywhere over Tailscale.

## Features

- Add, edit, and delete kits (name, grade, kit number, series, status, difficulty, build quality, notes)
- Build progress on every kit: Not Started, Snapped Fit, Built, Painted
- A finished date that fills in by itself when a kit is marked Built or Painted, and can be typed in by hand for kits I finished before I had the app
- Search kits by name, and sort them by name, grade, series, kit number, or status
- Series suggestions while typing, so the same series doesn't get spelled three different ways
- Paints inventory with a color swatch, brand, paint code, and how many I have on hand
- Search paints by name or paint code (like "C-5"), with −1 and +1 buttons for when I finish or buy a jar
- Paints I've used up are kept, not deleted, and hidden until I ask to see them
- Tools and supplies inventory, sorted by category, with a "running low" flag for things that run out like sandpaper and cement
- Works on phones, with light and dark mode
- A shading mixer for every paint: slide toward darker or lighter and get a mixing ratio with black or white, with a preview that mixes like real pigment

## Built With

- Python and Flask
- SQLite (Python's built-in sqlite3, no ORM)
- Jinja templates, HTML, and CSS
- pytest, including page tests with Flask's test client
- [Mixbox](https://github.com/scrtwpns/mixbox) for pigment-style color mixing (CC BY-NC 4.0, free for non-commercial use)

## How the Finished Date Works

| What happens | Finished date |
| --- | --- |
| A new kit is added as Built or Painted with no date | Today |
| A date is typed in (backfilling an older build) | The typed date |
| Status changes from Built to Painted and the date isn't touched | Moves to today |
| The date is changed by hand | The typed date |
| Status changes back to Not Started or Snapped Fit | Cleared |

## Project Structure

```
gunpla-tracker/
├── app.py              # Routes and page logic
├── kits.py             # Kit form checks, the finished-date rule, and sorting
├── paints.py           # Paint form checks and the +1/-1 rule
├── tools.py            # Tool form checks and sorting
├── shading.py          # Shading mixer: ratios and pigment-style color mixing
├── forms.py            # Small helpers shared by every form
├── db.py               # Database connection, setup, and the search helper
├── schema.sql          # Database tables
├── templates/          # Jinja page templates
├── static/style.css    # Styles
├── tests/              # pytest tests
└── docs/               # Design and build plan
```

## Running It Locally

```
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5001. The database (`kits.db`) is created automatically on the first run.

> **Note:** there is no login, so only run this on a private network. Don't expose it to the internet.

## Running It with Docker

1. Create a `.env` file next to `compose.yaml` with a random secret key:

   ```
   SECRET_KEY=your-long-random-string
   ```

   One way to make one: `python3 -c "import secrets; print(secrets.token_hex(32))"`

2. Build and start it:

   ```
   docker compose up -d --build
   ```

3. Open http://localhost:5001 (or your server's address on port 5001).

The database is stored in `./data`, outside the container, so it survives rebuilds. Back up that folder.

## Running the Tests

```
pip install -r requirements-dev.txt
pytest
```

Each test gets its own empty database, so running the tests never touches my real collection.

## What I Learned

- Writing each test before the code and watching it fail first. Two tests passed before their feature even existed, which meant they weren't testing anything, so they had to be rewritten.
- Testing whole pages with Flask's test client, not just single functions
- Giving every test its own temporary database with pytest fixtures and `monkeypatch`
- Keeping the rules (form checks, dates, sorting) in their own file so they can be tested without a web page
- Making `%` and `_` in a search match literally in a SQL `LIKE` search
- Sorting with key functions and tuples, and putting missing values last so Python never has to compare a number with `None`
- Using GET for searches and POST for anything that changes data, so following a link can never delete a kit
- CSS variables for light and dark mode, and `clip-path` for the cut corners on the cards
- Refactoring: moving shared helpers into their own files, with the existing tests proving nothing broke
- Building a SQL query from parts (only the filters that are needed), while every value still goes through `?` placeholders
- Checking input with a regular expression before it goes into the page, like the paint color in the swatch
- Adding new tables to an existing database with `CREATE TABLE IF NOT EXISTS`, without touching the data already there
- Passing data from Python to JavaScript with Jinja's `tojson`, so a slider can update the page without reloading it
- Keeping the math in Python, where pytest can check it, and letting JavaScript only display the result
- Checking a library's license before adding it to a project

## Roadmap

- Scan paint barcodes with my phone camera, and remember them for rebuys

This is a personal fan project and isn't affiliated with Bandai.