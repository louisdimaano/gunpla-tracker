# Gunpla Tracker: Design

Date: 2026-11-14
Owner: Louis Dimaano

## Intent

A phone-friendly web app for everything on Louis's Gunpla bench: the kits he owns, the paints he has, and his tools and supplies. The main moments it serves:

- **"What do I have?"** Looking through his kits and their status from his phone.
- **"Do I already own this paint?"** Standing in a hobby store, searching his paints by name.
- **"What should I build next?"** A light nudge based on his own build plan and his notes on past kits.
- **"How do I mix this shade?"** Picking a paint he owns and getting a lighter or darker mixing ratio.

It is also a portfolio project and a learning project. Louis is currently on a break from building, so the near-term value is the learning and the GitHub repo; day-to-day use comes when he's building again.

## How it gets built (decided)

Louis decided to build it like his SpoolManager project (github.com/louisdimaano/spool-manager). That means the same stack and the same shape:

- Python and Flask
- SQLite through Python's built-in `sqlite3` (no ORM)
- Jinja templates, HTML, CSS, and a small amount of JavaScript
- Gunicorn and Docker Compose, running on his homelab (an old Dell laptop with Ubuntu Server)
- pytest for tests
- A README in the same style: Features, Built With, Project Structure, Running It, What I Learned, Roadmap
- A similar file layout: `app.py`, `db.py`, `schema.sql`, `templates/`, `static/style.css`, `tests/`, plus a module for the mixer math (like `filament.py` holds SpoolManager's math)

Louis learns by building step by step with guidance. The plan should be broken into small steps he can follow, with every piece of code explained in plain, non-technical terms, including why it's there. He is a Python-first backend learner; frontend is secondary.

## Goals

1. **Kits.** Add, edit, and delete kits. Each kit has:
   - name (for example "Gundam Exia")
   - grade (HG, RG, MG, plus others such as PG, SD, EG, FM, Other; the exact list is the builder's call)
   - series or line (free text, for example "HG Gundam 00", "MG Ver.Ka")
   - kit number (optional, for example RG 15)
   - status: Not Started, Snapped Fit, Built, Painted
   - difficulty (rating)
   - build quality (rating; describes how the kit itself holds together, for example the Exia MG "falls apart")
   - notes (free text)
   - finished date: saved automatically when the status changes to Built or Painted, and editable by hand so kits he already built can be backfilled (Claude's call; the next-build helper needs it, so it belongs in the first version of the kits table)
   - Browse and sort by grade, series, kit number, and status. Search by name.

2. **Paints.** An inventory he can search by name from his phone. Searching shows only paints he owns that match; no result means he doesn't own it. Each paint has a name, brand, an optional paint code (like "C-5"), a color swatch (picked with a color picker when adding), a quantity count (how many jars or bottles), a "running low" flag, and notes. When the count reaches zero the paint is **kept, not deleted**, so its barcode is remembered for a rebuy. Used-up paints are hidden from the normal search so search only shows what he actually has, but scanning a used-up paint's barcode still finds it and offers to add one (Claude's call).

3. **Tools and supplies.** Nippers, scribes, hobby knives, sanding sticks, sandpaper, panel liners, top coats, and so on. Two kinds:
   - things he owns once (mostly "do I have this?")
   - things that run out (with a "running low" flag, like SpoolManager's LOW badge)
   Notes field (for example "these nippers leave stress marks"). Searchable by name.

4. **Paint barcode scanning, learned as you go.** No outside barcode catalog. The first time he scans a paint, he types its details and the app saves that barcode with the paint. Scanning the same barcode later finds the paint right away and offers to add one more. Kits and tools are typed in by hand, not scanned.

5. **Reachable away from home.** Runs on the homelab in Docker. Tailscale (installed on the homelab and his phone) lets his phone reach it from anywhere, privately. It is never exposed to the public internet.

6. **Next-build helper.** A light suggestion, not a rule. It follows Louis's own plan: build HGs first to master building and painting, then alternate RG and HG so he doesn't burn out. It suggests kits from his Not Started list that fit the next step, and shows his notes and ratings so a bad past experience (low build quality) is visible when choosing. Rules Louis decided:
   - A kit only counts as finished when its status is **Painted** (his goal is to master painting).
   - The HG-first phase ends **automatically after a number of painted HGs**. That number is a setting he can change in the app (the default is Claude's call; 5 is a reasonable start).
   - After that, the helper alternates: if the most recently painted kit (by finished date) was an HG, suggest RGs; if it was an RG, suggest HGs.
   - MG, PG, SD, and other grades are **left out by default**, with a setting to include them when he chooses. How included grades fit into the alternation is the builder's call (for example, treated as a "wild card" that doesn't change whose turn it is).

7. **Shading mixer.** Pick a paint he owns, move a slider toward lighter or darker, and get a mixing ratio in whole parts, like "4 parts base : 1 part white." Lighter mixes toward white and darker toward black. The page clearly says the result is a starting point to test, because screen colors only estimate how real paint mixes.

## Later, optional (not part of the first build)

- **Two-color mixing toward a target color**, built on Mixbox (a free library that simulates real pigment mixing). For when he has a custom "vision." Lower priority than shading because he mainly paints kits in their own colors.
- **Linking paints to kits** ("Exia uses these paints," so he can see whether he owns everything before starting). This was Claude's suggestion; Louis has not asked for it.

## Build order

1. Kits (goal 1)
2. Paints and tools inventory with search (goals 2 and 3)
3. Docker on the homelab, reachable over the existing Tailscale setup (goal 5)
4. Next-build helper (goal 6)
5. Shading mixer (goal 7)
6. Paint barcode scanning (goal 4)

Each stage should leave a working app that's useful on its own. Scanning is placed last by Claude's call because it depends on HTTPS (see Constraints) and adds the most moving parts.

## Non-goals

- **Collecting sets.** Louis explicitly dropped this: he doesn't want every kit in a series, so there's no "4 of 6" completion tracking and no "Wanted" status.
- **An outside catalog of kits or paints.** Everything comes from what he enters.
- **Custom painting workflows.** He paints kits in their own colors.
- **Public access.** No public URL, no sharing with others.

## Anti-goals

- **Punishing breaks.** Louis said the thing that would make him stop using it is taking a break from Gunpla, which is where he is now. So: no reminders, no streaks, no "you haven't built in X days," nothing that goes stale or breaks while it sits unused. Coming back months later, everything is where he left it.
- **Stalling the project on the fun part.** The mixer is the most interesting feature but must not be started before the inventory works.

## Constraints

- Must be comfortable to use on a phone (main device). Desktop is secondary.
- Runs alongside SpoolManager on the same homelab. SpoolManager uses host port 5000, so this needs a different port.
- Data lives in a mounted volume outside the container (like SpoolManager's `./data`) so it survives rebuilds.
- Secrets come from a `.env` file, never from code.
- **Camera access needs HTTPS.** Phone browsers only allow a web page to use the camera on a secure (HTTPS) connection. Plain `http://` over Tailscale won't allow scanning. Tailscale can provide HTTPS for devices on the private network (`tailscale serve` or `tailscale cert`); the builder should plan for that before the scanning stage.
- **Tailscale is already set up** (Nov 2026): installed on the homelab (Tailscale address `100.66.60.85`, MagicDNS name `homelab`, key expiry disabled), his PC, and his phone, and tested over mobile data. The server ran `tailscale up --accept-dns=false`. Apps already on the server: Uptime Kuma (port 3001), AdGuard Home (port 3000), and SpoolManager (port 5000), so the tracker needs a different port. Over Tailscale, apps are opened as `http://homelab:<port>`.
- **HTTPS is not set up yet.** Stage 3 only needs to deploy the app and confirm it opens on his phone over Tailscale. HTTPS for camera scanning (through Tailscale) is set up at the start of the scanning stage, in a way that leaves room for SpoolManager too.
- Louis keeps a "Homelab Notes" doc with a change log for the server; homelab changes made in stage 3 should be added to it.
- He backs up the homelab to Backblaze B2; the tracker's data folder should be included in those backups.
- No login is required as long as it's only reachable through Tailscale (only Louis's own devices can reach it). SpoolManager's README notes a login would be needed before it's reachable outside the home network; Tailscale is the answer to that here, and the README should say so.

## Left to the builder

- Exact database tables and columns
- The rating scale for difficulty and build quality
- The full grade list
- Page layout and styling (can reuse SpoolManager's look, light and dark mode)
- The color math for shading (any reasonable approach that gives whole-number ratios)
- Which barcode scanning library to use in the browser
- Repository name (for example `gunpla-tracker`) and the host port
