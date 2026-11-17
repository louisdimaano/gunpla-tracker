# Gunpla Tracker Stage 3 (Homelab Deploy) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For this project specifically:** Louis does every step himself (Windows PC and SSH into his homelab), guided step by step, with each command explained in plain terms before he runs it.

**Goal:** Gunpla Tracker runs in Docker on Louis's homelab, starts on its own after reboots, keeps its data outside the container, and opens on his phone anywhere at `http://homelab:5001` over Tailscale.

**Architecture:** The same setup as SpoolManager: a `Dockerfile` builds the app on `python:3.13-slim` and runs it with Gunicorn on container port 8000; `compose.yaml` maps host port 5001 to it, mounts `./data` for the database, and reads `SECRET_KEY` from a `.env` file. The code is cloned from GitHub into `~/gunpla-tracker` on the server; future updates are `git pull` then `docker compose up -d --build`.

**Tech Stack:** Docker, Docker Compose, Gunicorn, Tailscale (already set up), Uptime Kuma and Homepage (already running).

**Spec:** `docs/superpowers/specs/2026-11-14-gunpla-tracker-design.md` (Goal 5; build order step 3; Constraints on ports, data, secrets, and backups)

## Global Constraints

- Host port **5001** (3000 AdGuard, 3001 Uptime Kuma, and 5000 SpoolManager are taken)
- The database lives in `~/gunpla-tracker/data` on the server, outside the container, so rebuilds never touch it
- `SECRET_KEY` lives only in `~/gunpla-tracker/.env` on the server (permissions 600), never in Git
- Reachable only over Tailscale; no public URL, no router port forwarding
- The compose file is named **`compose.yaml`**, because the weekly update script only updates folders that contain a file with exactly that name
- No code changes to the app; the 77 tests must still pass

## Review Focus

1. **The weekly update script skipping the app.** The script looks for `compose.yaml` specifically. A file named `docker-compose.yml` (SpoolManager's name) would be silently skipped, so the app would never get a patched Python base image. Checked in Task 3.
2. **Losing the real collection.** Louis's kits, paints, and tools are in `kits.db` on his PC. Copying it to the server has to happen while the app is stopped on both sides, or the copy can be incomplete. Covered in Task 2.
3. **The database ending up inside the image.** `.dockerignore` already excludes `*.db`, `data/`, and `.env`, so `docker compose build` never bakes a database or the secret into the image. Checked in Task 1.
4. **Starting after a reboot or a nightly backup.** `restart: unless-stopped` brings it back after a reboot, and the backup script restarts whatever was running. Checked in Task 2 with a manual restart.
5. **Silent downtime.** An Uptime Kuma monitor alerts his phone if the app stops answering. Added in Task 3.

---

### Task 1: Docker files (on the PC)

**Files:**
- Create: `Dockerfile`, `compose.yaml`
- Modify: `README.md` (add "Running It with Docker")

- [ ] **Step 1: `Dockerfile`:** same as SpoolManager's, with `ENV DATABASE_PATH=/data/kits.db`
- [ ] **Step 2: `compose.yaml`:** service and container name `gunpla-tracker`, `build: .`, ports `"5001:8000"`, `SECRET_KEY=${SECRET_KEY}`, volume `./data:/data`, `restart: unless-stopped`
- [ ] **Step 3: README:** add a "Running It with Docker" section (create `.env`, `docker compose up -d --build`, port 5001, data in `./data`), mirroring SpoolManager's; mention the app runs on the homelab in the intro
- [ ] **Step 4: Verify:** `pytest` (77 passed); `git status` shows only `Dockerfile`, `compose.yaml`, and `README.md`
- [ ] **Step 5: Commit and push:** `git commit -m "Add Docker setup for the homelab"` then `git push`

### Task 2: Deploy on the homelab (over SSH)

- [ ] **Step 1:** `ssh onaamid@homelab`, then `git clone https://github.com/louisdimaano/gunpla-tracker.git` in the home folder, then `cd gunpla-tracker`
- [ ] **Step 2: Secret key:** generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`, put it in `.env` as `SECRET_KEY=...` with `nano`, then `chmod 600 .env`
- [ ] **Step 3 (optional): Bring the real collection over:** on the server `mkdir data`; on the PC, with the app stopped, run `scp kits.db onaamid@homelab:~/gunpla-tracker/data/kits.db` from the project folder. Skip this to start empty.
- [ ] **Step 4: Start it:** `docker compose up -d --build`. Expected: `docker ps` lists `gunpla-tracker` as `Up`, and `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5001/` prints `200`
- [ ] **Step 5: Phone test:** Wi-Fi off, Tailscale on, open `http://homelab:5001`; the kits (and paints and tools, if copied) are there
- [ ] **Step 6: Restart test:** `docker compose restart`, reload the page, and check the data is still there

### Task 3: Fit it into the homelab

- [ ] **Step 1: Update script:** `sudo cat /usr/local/bin/homelab-update.sh` and confirm the loop checks for `compose.yaml` and includes `docker compose build --pull`. Also check whether SpoolManager's folder (which uses `docker-compose.yml`) is being skipped; if so, fix it (rename its file to `compose.yaml` and push, or let the script check both names).
- [ ] **Step 2: Backups:** nothing to change; the nightly backup already covers all of `/home/onaamid`, which includes `~/gunpla-tracker/data` and `.env`
- [ ] **Step 3: Uptime Kuma:** add an HTTP monitor named "Gunpla Tracker" for `http://100.66.60.85:5001`
- [ ] **Step 4: Homepage:** add a Gunpla Tracker tile linking to `http://homelab:5001`, next to SpoolManager
- [ ] **Step 5: Homelab Notes:** add a quick reference row and a change log entry (folder, port, how to deploy updates)
