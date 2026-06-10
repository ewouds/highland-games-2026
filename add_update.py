#!/usr/bin/env python3
"""
Highland Games — add an update to the travel diary and publish.

Usage:
  add_update.py --date 2026-06-10 --time "14:30" --text "..." [--photo /path/img.jpg "caption"] [--photo ...]
  add_update.py --date today ...            (today resolves to trip day in Europe/Brussels)
  add_update.py --rebuild                   (just rebuild + push, no new entry)

Photos are copied into ./photos/ with a timestamped name and referenced in journal.json.
After updating, it rebuilds index.html and git commit+push (token from Azure KV).

This script lives in the workspace repo (already cloned). It does: git pull --rebase, edit, build, commit, push.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import datetime
import re

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, "journal.json")
PHOTOS = os.path.join(HERE, "photos")

VALID_DATES = ["2026-06-10", "2026-06-11", "2026-06-12", "2026-06-13", "2026-06-14", "2026-06-15"]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=HERE, text=True, capture_output=True, **kw)


def get_token():
    import urllib.request
    req = urllib.request.Request(
        "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net",
        headers={"Metadata": "true"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        access = json.load(r)["access_token"]
    req2 = urllib.request.Request(
        "https://ews-kv-openclaw.vault.azure.net/secrets/github-token?api-version=7.4",
        headers={"Authorization": f"Bearer {access}"},
    )
    with urllib.request.urlopen(req2, timeout=10) as r:
        return json.load(r)["value"]


def resolve_date(d):
    if d in (None, "today"):
        # Brussels = UTC+2 in June (CEST)
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        ds = now.strftime("%Y-%m-%d")
    else:
        ds = d
    if ds not in VALID_DATES:
        sys.exit(f"Date {ds} is outside the trip (10–15 June 2026). Valid: {VALID_DATES}")
    return ds


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:40] or "photo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="today")
    ap.add_argument("--time", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--lat", default=None, help="GPS latitude (decimal)")
    ap.add_argument("--lon", default=None, help="GPS longitude (decimal)")
    ap.add_argument("--photo", action="append", nargs="+", metavar=("PATH", "CAPTION"),
                    help="Path then optional caption. Repeatable.")
    ap.add_argument("--rebuild", action="store_true", help="Only rebuild+push, no new entry")
    ap.add_argument("--delete-ref", type=int, default=None, metavar="N",
                    help="Delete the entry with REF-N (across all days), then rebuild+push.")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    # pull latest first
    pull = run(["git", "pull", "--rebase", "origin", "main"])
    if pull.returncode != 0:
        print("WARN git pull:", pull.stderr.strip()[:300])

    with open(JOURNAL, encoding="utf-8") as f:
        data = json.load(f)

    if args.delete_ref is not None:
        target = args.delete_ref
        removed = None
        for _d in data["days"]:
            ents = _d.get("entries", [])
            for i, _e in enumerate(ents):
                if _e.get("ref") == target:
                    removed = ents.pop(i)
                    removed_day = _d.get("date")
                    break
            if removed is not None:
                break
        if removed is None:
            sys.exit(f"No entry with REF-{target:03d} found.")
        with open(JOURNAL, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Deleted REF-{target:03d} from {removed_day}: {removed.get('text','')[:60]}...")

    if not args.rebuild and args.delete_ref is None:
        date = resolve_date(args.date)
        day = next((d for d in data["days"] if d["date"] == date), None)
        if day is None:
            sys.exit(f"No day {date} in journal")

        photos = []
        if args.photo:
            os.makedirs(PHOTOS, exist_ok=True)
            stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            for i, pv in enumerate(args.photo):
                src = pv[0]
                cap = pv[1] if len(pv) > 1 else ""
                if not os.path.isfile(src):
                    print(f"WARN photo not found: {src}")
                    continue
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                base = f"{date}-{stamp}-{i+1}-{slugify(cap) if cap else 'foto'}{ext}"
                dst = os.path.join(PHOTOS, base)
                shutil.copy2(src, dst)
                photos.append({"file": base, "caption": cap})

        # assign next unique REF number (persisted in meta.nextRef)
        nextref = data.get("meta", {}).get("nextRef")
        if not isinstance(nextref, int):
            mx = 0
            for _d in data["days"]:
                for _e in _d.get("entries", []):
                    if isinstance(_e.get("ref"), int):
                        mx = max(mx, _e["ref"])
            nextref = mx + 1
        entry = {"ref": nextref, "time": args.time, "text": args.text, "photos": photos}
        if args.lat and args.lon:
            entry["location"] = {"lat": float(args.lat), "lon": float(args.lon)}
        # skip fully-empty entries
        if entry["text"] or entry["photos"]:
            day.setdefault("entries", []).append(entry)
            data.setdefault("meta", {})["nextRef"] = nextref + 1
            with open(JOURNAL, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Added entry REF-{nextref:03d} to {date}: text={'yes' if args.text else 'no'}, photos={len(photos)}")
        else:
            print("Nothing to add (no text, no photos). Rebuilding only.")

    # build
    b = run([sys.executable, "build.py"])
    print(b.stdout.strip() or b.stderr.strip())
    if b.returncode != 0:
        sys.exit("Build failed")

    if args.no_push:
        print("Skipping push (--no-push).")
        return

    # commit + push
    run(["git", "add", "-A"])
    if args.rebuild:
        msg = "Rebuild"
    elif args.delete_ref is not None:
        msg = f"Delete REF-{args.delete_ref:03d}"
    else:
        msg = f"Update {resolve_date(args.date)}"
    c = run(["git", "commit", "-m", f"Highland Games: {msg}"])
    if "nothing to commit" in (c.stdout + c.stderr):
        print("No changes to commit.")
        return
    tok = get_token()
    push_url = f"https://x-access-token:{tok}@github.com/ewouds/highland-games-2026.git"
    p = run(["git", "push", push_url, "main"])
    if p.returncode == 0:
        print("Pushed ✅ → https://ewouds.github.io/highland-games-2026/")
    else:
        print("Push failed:", p.stderr.strip()[:400])
        sys.exit(1)


if __name__ == "__main__":
    main()
