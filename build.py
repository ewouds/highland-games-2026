#!/usr/bin/env python3
"""Build index.html for The Highland Games travel diary from journal.json."""
import json
import html
import os
import urllib.parse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, "journal.json")
OUT = os.path.join(HERE, "index.html")

# Airport coordinates (lat, lon) for the map
COORDS = {
    "EBAW": (51.1894, 4.4603),
    "EGSC": (52.2050, 0.1750),
    "EGCM": (53.8665, -1.0090),
    "EGPG": (55.9747, -3.9747),
    "EGPR": (57.0228, -7.4431),
    "EGPE": (57.5425, -4.0475),
    "EGEO": (56.4636, -5.3997),
    "EGAD": (54.5811, -5.6919),
    "EIKY": (52.1809, -9.5238),
    "EGFF": (51.3967, -3.3433),
    "EGSU": (52.0908, 0.1314),
}


def load():
    with open(JOURNAL, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_time(mins):
    if mins is None:
        return ""
    h = int(mins // 60)
    m = int(round(mins % 60))
    if h:
        return f"{h}u{m:02d}"
    return f"{m} min"


# Vaste deelnemerslijst (hoofdlettergevoelig) — bron voor de deelnemer-filter.
PARTICIPANTS = [
    "Annick", "Axel", "Brecht", "Dirk", "Ewoud", "Glenn", "Hans", "Josha",
    "Ken", "Koen V", "Koenraad VB", "Kristof", "Lieven", "Luk", "Marc",
    "Michael", "Nick", "Tom", "Wim",
]


def pslug(name):
    """Veilige, stabiele slug voor data-attributen (bv. 'Koen V' -> 'koen-v')."""
    return name.lower().replace(" ", "-")


def crew_member(name, role):
    """Render one crew member chip with role styling."""
    cls = {"PIC": "pic", "COPILOT": "copilot"}.get(role, "pax")
    chip = f'<span class="crew">{html.escape(name)}</span>'
    return (
        f'<span class="seat {cls}" data-person="{pslug(name)}">'
        f'<span class="seat-role">{html.escape(role)}</span>{chip}</span>'
    )


def render_aircraft_crew(ac):
    """Render one aircraft row: reg + PIC + Copilot + PAX list."""
    reg = ac.get("reg", "")
    seats = []
    names = []
    if ac.get("pic"):
        seats.append(crew_member(ac["pic"], "PIC"))
        names.append(ac["pic"])
    if ac.get("copilot"):
        seats.append(crew_member(ac["copilot"], "COPILOT"))
        names.append(ac["copilot"])
    for p in (ac.get("pax", []) or []):
        seats.append(crew_member(p, "PAX"))
        names.append(p)
    people = " ".join(pslug(n) for n in names)
    return (
        f'<div class="ac-row" data-people="{html.escape(people)}">'
        f'<span class="ac-reg">{html.escape(reg)}</span>'
        f'<span class="ac-seats">{"".join(seats)}</span>'
        '</div>'
    )


def build_route_points(data):
    """Ordered unique airport sequence across the whole trip."""
    seq = []
    for day in data["days"]:
        for leg in day.get("legs", []):
            if not seq or seq[-1] != leg["from"]:
                if not seq:
                    seq.append(leg["from"])
                elif seq[-1] != leg["from"]:
                    seq.append(leg["from"])
            seq.append(leg["to"])
    # de-dup consecutive
    out = []
    for s in seq:
        if not out or out[-1] != s:
            out.append(s)
    return out


def render_entry(entry):
    """An entry: {ref:int, text, photos:[{file,caption}], time}"""
    _ref = entry.get('ref')
    ref_badge = (f'<span class="entry-ref">REF-{_ref:03d}</span>' if isinstance(_ref, int) else '')
    parts = []
    t = entry.get("time", "")
    text = entry.get("text", "")
    photos = entry.get("photos", [])
    parts.append('<div class="entry">')
    if ref_badge or t:
        _t = f'<span class="entry-time-txt">{html.escape(t)}</span>' if t else ''
        parts.append(f'<div class="entry-time">{ref_badge}{_t}</div>')
    if text:
        # naive paragraph split
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                parts.append(f'<p>{html.escape(para)}</p>')
    if photos:
        parts.append('<div class="gallery">')
        for p in photos:
            f = html.escape(p.get("file", ""))
            cap = html.escape(p.get("caption", ""))
            parts.append(
                f'<figure><a href="photos/{f}" data-lightbox><img loading="lazy" src="photos/{f}" alt="{cap}"></a>'
                + (f'<figcaption>{cap}</figcaption>' if cap else "")
                + '</figure>'
            )
        parts.append('</div>')
    parts.append('</div>')
    return "\n".join(parts)



def render_prep_section(prep_days):
    """Render all preparation days bundled into one collapsible section."""
    if not prep_days:
        return ""
    days = sorted(prep_days, key=lambda d: d.get("date", ""))
    parts = []
    parts.append('<section class="day prep prep-section" id="voorbereiding">')
    parts.append('<details class="prep-collapse">')
    parts.append(
        '<summary><span class="prep-ico">📝</span> Voorbereiding '
        f'<span class="prep-count">{len(days)} momenten</span>'
        '<span class="sum-hint">(klik om te tonen)</span></summary>'
    )
    parts.append('<div class="prep-body">')
    for day in days:
        dt = f'{day["date"][8:10]}/{day["date"][5:7]}'
        parts.append('<div class="prep-item">')
        parts.append(
            f'<div class="prep-item-head"><span class="prep-date">{html.escape(dt)}</span>'
            f'<span class="prep-label">{html.escape(day.get("label", ""))}</span></div>'
        )
        entries = day.get("entries", [])
        if entries:
            for e in entries:
                parts.append(render_entry(e))
        else:
            parts.append('<div class="entries empty">Nog geen updates.</div>')
        parts.append('</div>')
    parts.append('</div>')
    parts.append('</details>')
    parts.append('</section>')
    return "\n".join(parts)

def render_hotel(h):
    """Overnachtingskaart per dag. h = {city,name,checkin,checkout,booked_by,cancel_by,nights?,note?,rooms?}"""
    parts = []
    nights = h.get("nights")
    nights_badge = f'<span class="htl-nights">{nights} nachten</span>' if nights and nights > 1 else ''
    parts.append('<div class="hotel">')
    parts.append(
        f'<div class="htl-head"><span class="htl-ico">\U0001F6CF\uFE0F</span>'
        f'<div class="htl-title"><span class="htl-city">{html.escape(h.get("city",""))}</span>'
        f'<span class="htl-name">{html.escape(h.get("name",""))}</span></div>'
        f'{nights_badge}</div>'
    )
    # meta-rij: data + boeker + annuleerdeadline
    rows = []
    ci, co = h.get("checkin"), h.get("checkout")
    if ci and co:
        rows.append(f'<span class="htl-row"><span class="htl-k">\U0001F4C5</span>{html.escape(ci)} \u2192 {html.escape(co)}</span>')
    if h.get("booked_by"):
        rows.append(f'<span class="htl-row"><span class="htl-k">\U0001F465</span>{html.escape(h["booked_by"])}</span>')
    if h.get("address"):
        _q = urllib.parse.quote(f'{h.get("name","")} {h["address"]}')
        _maps = f'https://www.google.com/maps/search/?api=1&query={_q}'
        rows.append(
            f'<span class="htl-row htl-addr"><span class="htl-k">\U0001F4CD</span>'
            f'<a href="{_maps}" target="_blank" rel="noopener">{html.escape(h["address"])}</a></span>'
        )
    if h.get("cancel_by"):
        rows.append(f'<span class="htl-row htl-cancel"><span class="htl-k">\u23F0</span>gratis annuleerbaar tot {html.escape(h["cancel_by"])}</span>')
    if rows:
        parts.append('<div class="htl-meta">' + "".join(rows) + '</div>')
    if h.get("note"):
        parts.append(f'<div class="htl-note">{html.escape(h["note"])}</div>')

    # kamerverdeling (inklapbaar) — ondersteunt 'items' of gegroepeerde 'groups'
    rooms = h.get("rooms")
    if rooms:
        def room_row(it):
            g = html.escape(it.get("guests", "") or "")
            guests_html = f'<span class="rm-guests">{g}</span>' if g else '<span class="rm-guests rm-empty">\u2014</span>'
            pax = it.get("pax")
            pax_html = f'<span class="rm-pax">{pax}p</span>' if isinstance(pax, int) else ''
            return (f'<div class="rm-row"><span class="rm-type">{html.escape(it.get("type",""))}</span>'
                    f'{guests_html}{pax_html}</div>')
        parts.append('<details class="rooms-details">')
        parts.append(f'<summary><span class="sum-ico">\u2630</span> {html.escape(rooms.get("title","Kamerverdeling"))} <span class="sum-hint">(klik om te tonen)</span></summary>')
        parts.append('<div class="rooms-body">')
        if rooms.get("groups"):
            for grp in rooms["groups"]:
                if grp.get("label"):
                    parts.append(f'<div class="rm-group-label">{html.escape(grp["label"])}</div>')
                for it in grp.get("items", []):
                    parts.append(room_row(it))
        else:
            for it in rooms.get("items", []):
                parts.append(room_row(it))
        parts.append('</div>')
        parts.append('</details>')
    parts.append('</div>')
    return "\n".join(parts)


def render_day(data, day):
    ap = data["airports"]
    parts = []
    rest = day.get("restDay")
    prep = day.get("prep")
    cls = " prep" if prep else (" rest" if rest else "")
    parts.append(f'<section class="day{cls}" id="{day["date"]}">')
    parts.append('<div class="day-head">')
    if prep:
        parts.append(
            f'<div class="day-date"><span class="wd">{html.escape(day["date"][8:10])}/{html.escape(day["date"][5:7])}</span>'
            f'<span class="dt">PREP</span></div>'
        )
    else:
        parts.append(f'<div class="day-date"><span class="wd">{html.escape(day["weekday"])}</span><span class="dt">{html.escape(day["date"][8:10])}/{html.escape(day["date"][5:7])}</span></div>')
    parts.append(f'<h2>{html.escape(day["label"])}</h2>')
    parts.append('</div>')

    if prep:
        parts.append('<div class="prep-banner">📝 Voorbereiding — nog geen wielen van de grond, wel volop papierwerk. Gendecs, GAR\'s, PPR\'s, paspoorten &amp; ETA\'s.</div>')
    elif rest:
        parts.append('<div class="rest-banner">🛌 Rustdag — geen vluchten gepland. Tijd om de Highlands te proeven.</div>')
    else:
        # legs — kort overzicht (altijd zichtbaar)
        parts.append('<div class="legs">')
        for leg in day.get("legs", []):
            frm, to = leg["from"], leg["to"]
            parts.append('<div class="leg">')
            parts.append(
                f'<div class="leg-route"><span class="apt">{frm}</span>'
                f'<span class="apt-name">{html.escape(ap.get(frm, ""))}</span>'
                f'<span class="arrow">→</span>'
                f'<span class="apt">{to}</span>'
                f'<span class="apt-name">{html.escape(ap.get(to, ""))}</span></div>'
            )
            meta = f'{leg["dist_nm"]} NM · {fmt_time(leg.get("time_min"))}'
            parts.append(f'<div class="leg-meta">{meta}</div>')
            parts.append('</div>')
        parts.append('</div>')

        # crew-details (inklapbaar, opent op klik)
        has_crew = any(leg.get("crew") for leg in day.get("legs", []))
        if has_crew:
            parts.append('<details class="crew-details">')
            parts.append('<summary><span class="sum-ico">☰</span> Bemanning per vliegtuig <span class="sum-hint">(klik om te tonen)</span></summary>')
            parts.append('<div class="crew-body">')
            for leg in day.get("legs", []):
                crew = leg.get("crew") or []
                if not crew:
                    continue
                parts.append('<div class="crew-leg-block">')
                parts.append(
                    f'<div class="crew-leg-label"><span class="cll-apt">{leg["from"]}</span>'
                    f'<span class="cll-arr">→</span><span class="cll-apt">{leg["to"]}</span></div>'
                )
                parts.append('<div class="crew-grid">')
                for ac in crew:
                    parts.append(render_aircraft_crew(ac))
                parts.append('</div>')
                parts.append('</div>')
            parts.append('</div>')
            parts.append('</details>')

    # accommodatie (overnachting) — toont op zowel vlieg- als rustdagen
    hotel = day.get("hotel")
    if hotel:
        parts.append(render_hotel(hotel))

    # entries
    entries = day.get("entries", [])
    if entries:
        parts.append('<div class="entries">')
        for e in entries:
            parts.append(render_entry(e))
        parts.append('</div>')
    else:
        parts.append('<div class="entries empty">Nog geen updates voor deze dag.</div>')

    parts.append('</section>')
    return "\n".join(parts)


def main():
    data = load()
    meta = data["meta"]
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    data["meta"]["lastUpdated"] = now

    route = build_route_points(data)
    route_coords = [COORDS[a] for a in route if a in COORDS]
    markers = [{"code": a, "name": data["airports"].get(a, ""), "lat": COORDS[a][0], "lon": COORDS[a][1]} for a in dict.fromkeys(route) if a in COORDS]

    total_nm = sum(leg["dist_nm"] for day in data["days"] for leg in day.get("legs", []))
    total_min = sum(leg.get("time_min", 0) for day in data["days"] for leg in day.get("legs", []))
    n_legs = sum(len(day.get("legs", [])) for day in data["days"])
    n_photos = sum(len(e.get("photos", [])) for day in data["days"] for e in day.get("entries", []))

    prep_days = [d for d in data["days"] if d.get("prep")]
    trip_days = [d for d in data["days"] if not d.get("prep")]
    prep_html = render_prep_section(prep_days)
    days_html = prep_html + "\n" + "\n".join(render_day(data, d) for d in trip_days)

    # deelnemer-filter chips (alfabetisch, vaste lijst)
    chips = "".join(
        f'<button class="cf-chip" data-person="{pslug(n)}">{html.escape(n)}</button>'
        for n in sorted(PARTICIPANTS, key=lambda s: s.lower())
    )
    crew_filter_html = (
        '<details class="crew-filter" id="crewFilter">'
        '<summary class="cf-summary">'
        '<span class="cf-title">\U0001F50D Filter op deelnemer</span>'
        '<span class="cf-badge" id="cfBadge" hidden></span>'
        '<span class="cf-toggle-hint"></span>'
        '</summary>'
        '<div class="cf-body">'
        '<span class="cf-hint">Tik op een naam om alleen die vluchten te tonen — combineer meerdere namen.</span>'
        f'<div class="cf-chips">{chips}</div>'
        '<div class="cf-foot">'
        '<button class="cf-reset" id="cfReset">Reset</button>'
        '<span class="cf-count" id="cfCount"></span>'
        '</div>'
        '</div>'
        '</details>'
    )

    photo_line = f"Al <b>{n_photos}</b> foto's online." if n_photos else "De eerste beelden volgen snel."

    markers_json = json.dumps(markers)
    line_json = json.dumps(route_coords)

    css = CSS
    js = JS_TEMPLATE.replace("__MARKERS__", markers_json).replace("__LINE__", line_json)

    doc = f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(meta['title'])} — Fly-Out 2026</title>
<meta name="description" content="{html.escape(meta['subtitle'])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>{css}</style>
</head>
<body>
<header class="hero">
  <div class="hero-inner">
    <div class="kicker">RAAC · FLY-OUT 2026 🏴󠁧󠁢󠁳󠁣󠁴󠁿</div>
    <h1>{html.escape(meta['title'])}</h1>
    <p class="sub">{html.escape(meta['subtitle'])}</p>
    <p class="tagline">{html.escape(meta.get('tagline',''))}</p>
    <div class="stats">
      <div class="stat"><b>6</b><span>dagen</span></div>
      <div class="stat"><b>{n_legs}</b><span>legs</span></div>
      <div class="stat"><b>{total_nm}</b><span>NM</span></div>
      <div class="stat"><b>{fmt_time(total_min)}</b><span>vliegtijd</span></div>
      <div class="stat"><b>6</b><span>vliegtuigen</span></div>
    </div>
  </div>
</header>

<div id="map"></div>

<main>
  <div class="intro">
    <p>Welkom op het live reisverslag van onze Fly-Out naar Schotland & Ierland. We vertrekken op <b>woensdag 10 juni</b> vanuit Antwerpen (EBAW) en zijn <b>maandag 15 juni</b> terug. Onderweg landen we op legendarische velden — van het strand van <b>Barra</b> tot de Highlands van <b>Inverness</b> en de Ierse westkust.</p>
    <p>Dit verslag wordt onderweg bijgewerkt met foto's en verhalen. {photo_line}</p>
  </div>

  {crew_filter_html}

  {days_html}
</main>

<footer>
  <p>✈️ The Highland Games · Fly-Out 2026 · gemaakt door Ewoud's Koda 🐾</p>
  <p class="updated">Laatst bijgewerkt: {now}</p>
</footer>

<div id="lightbox" class="lightbox" hidden>
  <button class="lb-close" aria-label="Sluiten">&times;</button>
  <img src="" alt="">
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>{js}</script>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    # persist lastUpdated back
    with open(JOURNAL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Built {OUT} ({len(doc)} bytes) — {n_photos} photos, {n_legs} legs, {total_nm} NM")


CSS = r"""
:root{
  --bg:#0b1220; --bg2:#0f1a2e; --card:#13203a; --line:#223150;
  --ink:#e8eefc; --muted:#9fb2d4; --accent:#48a9ff; --accent2:#7ee0c0;
  --pic:#48a9ff; --copilot:#7ee0c0; --pax:#b9a7ff; --rest:#ffcf6b;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,system-ui,sans-serif;background:
  radial-gradient(1200px 600px at 80% -10%, #16284a 0%, transparent 60%),
  radial-gradient(900px 500px at -10% 10%, #122038 0%, transparent 55%),
  var(--bg);color:var(--ink);line-height:1.6;-webkit-font-smoothing:antialiased}
.hero{position:relative;overflow:hidden;padding:84px 20px 64px;text-align:center;
  background:linear-gradient(180deg,#0a1020 0%, #0c1730 100%);border-bottom:1px solid rgba(72,169,255,.18)}
.hero:before{content:"";position:absolute;inset:0;
  background-image:radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,.5), transparent),
  radial-gradient(1px 1px at 60% 70%, rgba(255,255,255,.4), transparent),
  radial-gradient(1.5px 1.5px at 80% 20%, rgba(255,255,255,.3), transparent),
  radial-gradient(1px 1px at 35% 80%, rgba(255,255,255,.35), transparent);
  opacity:.6;pointer-events:none}
.hero-inner{position:relative;max-width:920px;margin:0 auto}
.kicker{letter-spacing:.28em;font-size:13px;font-weight:600;color:var(--accent);text-transform:uppercase;margin-bottom:14px}
h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(56px,11vw,128px);line-height:.92;margin:0;
  letter-spacing:.01em;background:linear-gradient(180deg,#fff,#9fc6ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{font-size:clamp(16px,2.4vw,22px);color:var(--ink);margin:14px 0 4px;font-weight:600}
.tagline{color:var(--muted);font-size:16px;margin:0 0 28px;font-style:italic}
.stats{display:flex;flex-wrap:wrap;gap:14px;justify-content:center;margin-top:8px}
.stat{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;
  padding:12px 18px;min-width:84px;backdrop-filter:blur(6px)}
.stat b{display:block;font-family:'Bebas Neue',sans-serif;font-size:30px;line-height:1;color:var(--accent2)}
.stat span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
#map{height:380px;width:100%;background:#0a1020;z-index:0}
.leaflet-container{background:#0a1020}
main{max-width:920px;margin:0 auto;padding:0 18px 40px}
.intro{padding:32px 4px 8px;color:var(--muted);font-size:17px}
.intro b{color:var(--ink)}
.day{margin:34px 0;background:linear-gradient(180deg,var(--card),#101b32);
  border:1px solid rgba(255,255,255,.07);border-radius:20px;padding:24px 22px;
  box-shadow:0 12px 40px rgba(0,0,0,.35)}
.day.rest{background:linear-gradient(180deg,#2a2113,#1c1810);border-color:rgba(255,207,107,.25)}
.day-head{display:flex;align-items:center;gap:18px;margin-bottom:18px}
.day-date{display:flex;flex-direction:column;align-items:center;justify-content:center;
  min-width:64px;height:64px;border-radius:16px;background:rgba(72,169,255,.12);
  border:1px solid rgba(72,169,255,.3);flex-shrink:0}
.day.rest .day-date{background:rgba(255,207,107,.12);border-color:rgba(255,207,107,.35)}
.day-date .wd{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.day-date .dt{font-family:'Bebas Neue',sans-serif;font-size:26px;line-height:1;color:var(--ink)}
.day-head h2{margin:0;font-size:clamp(20px,3.2vw,26px);font-weight:700}
.rest-banner{background:rgba(255,207,107,.1);border:1px dashed rgba(255,207,107,.4);
  border-radius:12px;padding:14px 16px;color:var(--rest);font-weight:500}
.day.prep{background:linear-gradient(180deg,#161f33,#101826);border-color:rgba(126,224,192,.22)}
.day.prep .day-date{background:rgba(126,224,192,.12);border-color:rgba(126,224,192,.35)}
.day.prep .day-date .dt{color:var(--accent2);font-size:15px;letter-spacing:.06em}
.prep-banner{background:rgba(126,224,192,.08);border:1px dashed rgba(126,224,192,.4);
  border-radius:12px;padding:14px 16px;color:var(--accent2);font-weight:500}
.prep-section{padding:0;overflow:hidden}
.prep-collapse summary{cursor:pointer;list-style:none;padding:16px 18px;font-size:16px;font-weight:700;
  color:var(--accent2);display:flex;align-items:center;gap:9px;user-select:none}
.prep-collapse summary::-webkit-details-marker{display:none}
.prep-collapse summary:hover{background:rgba(126,224,192,.06)}
.prep-ico{font-size:17px}
.prep-count{background:rgba(126,224,192,.16);color:var(--accent2);font-size:12px;font-weight:600;
  padding:2px 9px;border-radius:999px}
.prep-collapse[open] summary{border-bottom:1px solid rgba(126,224,192,.18)}
.prep-collapse[open] .sum-hint::after{content:"▲"}
.prep-collapse:not([open]) .sum-hint::after{content:"▼"}
.prep-body{padding:6px 18px 18px}
.prep-item{padding:14px 0;border-top:1px solid rgba(255,255,255,.06)}
.prep-item:first-child{border-top:none}
.prep-item-head{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}
.prep-date{font-family:'Bebas Neue',sans-serif;letter-spacing:.05em;color:var(--accent);font-size:20px}
.prep-label{font-weight:600;color:var(--ink);font-size:15px}
.entry-ref{display:inline-block;font-family:'Bebas Neue',sans-serif;letter-spacing:.07em;font-size:11px;color:var(--accent2);background:rgba(126,224,192,.12);border:1px solid rgba(126,224,192,.3);padding:1px 7px;border-radius:6px;margin-right:8px;vertical-align:middle;white-space:nowrap}

.legs{display:grid;gap:10px;margin-bottom:6px}
.leg{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);
  border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.leg-route{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.apt{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:.04em;color:var(--accent)}
.apt-name{font-size:13px;color:var(--muted)}
.arrow{color:var(--accent2);font-size:18px;margin:0 2px}
.leg-meta{font-size:13px;color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.crew-grid{display:grid;gap:7px;margin-top:4px}
.ac-row{display:flex;align-items:flex-start;gap:10px;padding:8px 10px;border-radius:10px;
  background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06)}
.ac-reg{font-family:'Bebas Neue',sans-serif;letter-spacing:.05em;color:var(--accent2);
  font-size:18px;min-width:74px;flex-shrink:0;padding-top:1px}
.ac-seats{display:flex;flex-wrap:wrap;gap:6px}
.seat{display:inline-flex;align-items:center;gap:5px;font-size:13px}
.seat-role{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
  padding:2px 6px;border-radius:6px}
.seat.pic .seat-role{background:rgba(72,169,255,.2);color:var(--pic)}
.seat.copilot .seat-role{background:rgba(126,224,192,.2);color:var(--copilot)}
.seat.pax .seat-role{background:rgba(185,167,255,.16);color:var(--pax)}
.crew{color:var(--ink)}
.crew-details{margin-top:10px;border:1px solid rgba(255,255,255,.08);border-radius:12px;
  background:rgba(255,255,255,.02);overflow:hidden}
.crew-details summary{cursor:pointer;list-style:none;padding:12px 14px;font-size:14px;font-weight:600;
  color:var(--ink);display:flex;align-items:center;gap:8px;user-select:none;transition:background .15s}
.crew-details summary::-webkit-details-marker{display:none}
.crew-details summary:hover{background:rgba(72,169,255,.07)}
.sum-ico{color:var(--accent);font-size:15px}
.sum-hint{color:var(--muted);font-weight:400;font-size:12px;margin-left:auto}
.crew-details[open] summary{border-bottom:1px solid rgba(255,255,255,.08)}
.crew-details[open] .sum-hint::after{content:"▲"}
.crew-details:not([open]) .sum-hint::after{content:"▼"}
.crew-body{padding:12px 14px 14px}
/* --- accommodatie / overnachting --- */
.hotel{margin-top:12px;border:1px solid rgba(126,224,192,.22);border-radius:12px;
  background:linear-gradient(180deg,rgba(126,224,192,.06),rgba(126,224,192,.02));overflow:hidden}
.htl-head{display:flex;align-items:center;gap:11px;padding:13px 15px}
.htl-ico{font-size:20px;line-height:1}
.htl-title{display:flex;flex-direction:column;gap:1px;min-width:0}
.htl-city{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent2);font-weight:700}
.htl-name{font-size:15px;font-weight:600;color:var(--ink)}
.htl-nights{margin-left:auto;flex:none;background:rgba(126,224,192,.16);color:var(--accent2);
  font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;white-space:nowrap}
.htl-meta{display:flex;flex-wrap:wrap;gap:7px 16px;padding:0 15px 13px;font-size:13px;color:var(--muted)}
.htl-row{display:inline-flex;align-items:center;gap:6px}
.htl-k{font-size:13px;opacity:.85}
.htl-cancel{color:var(--rest)}
.htl-addr a{color:var(--accent);text-decoration:none;border-bottom:1px dotted rgba(72,169,255,.4)}
.htl-addr a:hover{color:var(--accent2);border-bottom-color:var(--accent2)}
.htl-note{padding:0 15px 13px;font-size:12.5px;color:var(--muted);font-style:italic;margin-top:-4px}
.rooms-details{border-top:1px solid rgba(126,224,192,.16);background:rgba(255,255,255,.015)}
.rooms-details summary{cursor:pointer;list-style:none;padding:11px 15px;font-size:13.5px;font-weight:600;
  color:var(--ink);display:flex;align-items:center;gap:8px;user-select:none;transition:background .15s}
.rooms-details summary::-webkit-details-marker{display:none}
.rooms-details summary:hover{background:rgba(126,224,192,.07)}
.rooms-details[open] summary{border-bottom:1px solid rgba(126,224,192,.16)}
.rooms-details[open] .sum-hint::after{content:"\25B2"}
.rooms-details:not([open]) .sum-hint::after{content:"\25BC"}
.rooms-body{padding:10px 15px 13px;display:flex;flex-direction:column;gap:6px}
.rm-group-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);
  font-weight:700;margin-top:6px;margin-bottom:1px}
.rm-group-label:first-child{margin-top:0}
.rm-row{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.025);
  border:1px solid rgba(255,255,255,.06);border-radius:9px;padding:8px 11px}
.rm-type{font-weight:600;color:var(--ink);font-size:13.5px;flex:none;min-width:140px}
.rm-guests{color:var(--accent2);font-size:13px;flex:1}
.rm-guests.rm-empty{color:var(--muted);opacity:.5}
.rm-pax{flex:none;font-family:'Bebas Neue',sans-serif;letter-spacing:.04em;font-size:15px;
  color:var(--copilot);background:rgba(126,224,192,.14);border-radius:7px;padding:1px 9px}
.crew-leg-label{display:flex;align-items:center;gap:7px;margin:12px 0 7px;font-family:'Bebas Neue',sans-serif;
  letter-spacing:.04em;font-size:17px;color:var(--accent)}
.crew-leg-label:first-child{margin-top:2px}
.cll-arr{color:var(--accent2);font-size:14px}
.crew-leg-block{margin:0}
/* --- deelnemer-filter --- */
.crew-filter{margin:28px 0 4px;background:linear-gradient(180deg,var(--card),#101b32);
  border:1px solid var(--line);border-radius:18px;overflow:hidden;
  box-shadow:0 8px 30px rgba(0,0,0,.28)}
.cf-summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;
  padding:16px 18px;user-select:none;transition:background .15s}
.cf-summary::-webkit-details-marker{display:none}
.cf-summary:hover{background:rgba(72,169,255,.05)}
.cf-badge{background:rgba(72,169,255,.18);color:var(--accent);border:1px solid rgba(72,169,255,.45);
  font-size:12px;font-weight:700;padding:2px 10px;border-radius:999px;white-space:nowrap}
.cf-toggle-hint{margin-left:auto;color:var(--muted);font-size:13px;flex:none}
.crew-filter[open] .cf-toggle-hint::after{content:"\25B2 inklappen"}
.crew-filter:not([open]) .cf-toggle-hint::after{content:"\25BC openklappen"}
.crew-filter[open] .cf-summary{border-bottom:1px solid var(--line)}
.cf-body{padding:14px 18px 16px}
.cf-title{font-weight:700;font-size:16px;color:var(--ink);display:flex;align-items:center;gap:8px}
.cf-hint{font-size:12.5px;color:var(--muted);display:block;margin-bottom:12px}
.cf-chips{display:flex;flex-wrap:wrap;gap:8px}
.cf-chip{font-family:Inter,system-ui,sans-serif;font-size:13px;font-weight:600;cursor:pointer;
  color:var(--muted);background:rgba(255,255,255,.03);border:1px solid var(--line);
  border-radius:999px;padding:6px 14px;transition:background .15s,color .15s,border-color .15s}
.cf-chip:hover{color:var(--ink);border-color:rgba(72,169,255,.5);background:rgba(72,169,255,.08)}
.cf-chip.active{color:var(--accent);background:rgba(72,169,255,.18);
  border-color:rgba(72,169,255,.7);box-shadow:0 0 0 1px rgba(72,169,255,.25) inset}
.cf-foot{display:flex;align-items:center;gap:14px;margin-top:14px;flex-wrap:wrap}
.cf-reset{font-family:Inter,system-ui,sans-serif;font-size:12.5px;font-weight:600;cursor:pointer;
  color:var(--muted);background:transparent;border:1px solid var(--line);border-radius:9px;
  padding:6px 13px;transition:background .15s,color .15s,border-color .15s}
.cf-reset:hover{color:var(--rest);border-color:rgba(255,207,107,.5);background:rgba(255,207,107,.08)}
.cf-count{font-size:12.5px;color:var(--muted)}
.cf-count b{color:var(--accent2)}
/* highlight van geselecteerde deelnemer in de crew */
.seat.person-hit{background:rgba(255,207,107,.18);border-radius:8px;padding:2px 6px;
  box-shadow:0 0 0 1px rgba(255,207,107,.5),0 0 12px rgba(255,207,107,.25)}
.seat.person-hit .crew{color:var(--rest);font-weight:700}
.seat.cf-dim{opacity:.32;filter:saturate(.6)}
.cf-hidden{display:none !important}
.entries{margin-top:18px;display:grid;gap:18px}
.entries.empty{color:var(--muted);font-style:italic;font-size:14px;opacity:.7;margin-top:14px}
.entry{border-left:2px solid rgba(72,169,255,.3);padding-left:16px}
.entry-time{font-size:12px;color:var(--accent);font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
.entry p{margin:6px 0;color:var(--ink)}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-top:12px}
.gallery figure{margin:0;border-radius:12px;overflow:hidden;background:#0a1020;border:1px solid rgba(255,255,255,.08)}
.gallery img{width:100%;height:160px;object-fit:cover;display:block;cursor:zoom-in;transition:transform .3s}
.gallery img:hover{transform:scale(1.04)}
.gallery figcaption{font-size:12px;color:var(--muted);padding:8px 10px}
footer{text-align:center;padding:40px 20px 60px;color:var(--muted);font-size:14px;border-top:1px solid rgba(255,255,255,.06);margin-top:30px}
footer .updated{font-size:12px;opacity:.7;margin-top:6px}
.lightbox{position:fixed;inset:0;background:rgba(5,8,16,.94);display:flex;align-items:center;justify-content:center;z-index:1000;padding:20px;cursor:zoom-out}
.lightbox[hidden]{display:none}
.lightbox img{max-width:96vw;max-height:92vh;border-radius:8px;box-shadow:0 20px 80px rgba(0,0,0,.6)}
.lb-close{position:absolute;top:18px;right:24px;background:none;border:none;color:#fff;font-size:40px;cursor:pointer;line-height:1}
@media(max-width:560px){.day{padding:18px 14px}.gallery img{height:130px}}
"""

JS_TEMPLATE = r"""
(function(){
  var markers = __MARKERS__;
  var line = __LINE__;
  if(document.getElementById('map') && window.L){
    var map = L.map('map',{scrollWheelZoom:false,attributionControl:true});
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{
      attribution:'&copy; OpenStreetMap &copy; CARTO', maxZoom:19, subdomains:'abcd'
    }).addTo(map);
    var latlngs = line.map(function(p){return [p[0],p[1]];});
    if(latlngs.length){
      var poly = L.polyline(latlngs,{color:'#48a9ff',weight:3,opacity:.85,dashArray:'2,8',lineCap:'round'}).addTo(map);
      map.fitBounds(poly.getBounds().pad(0.15));
    }
    markers.forEach(function(m){
      var ic = L.divIcon({className:'apt-marker',html:'<div style="background:#7ee0c0;width:10px;height:10px;border-radius:50%;box-shadow:0 0 0 4px rgba(126,224,192,.25);border:2px solid #0a1020"></div>',iconSize:[10,10]});
      L.marker([m.lat,m.lon],{icon:ic}).addTo(map)
        .bindTooltip('<b>'+m.code+'</b> '+m.name,{direction:'top',offset:[0,-6]});
    });
  }
  // lightbox
  var lb = document.getElementById('lightbox');
  var lbImg = lb ? lb.querySelector('img') : null;
  document.addEventListener('click',function(e){
    var a = e.target.closest('a[data-lightbox]');
    if(a){ e.preventDefault(); lbImg.src=a.getAttribute('href'); lb.hidden=false; return; }
    if(lb && !lb.hidden && (e.target===lb || e.target.classList.contains('lb-close'))){ lb.hidden=true; lbImg.src=''; }
  });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&lb&&!lb.hidden){lb.hidden=true;lbImg.src='';}});

  // ---- deelnemer-filter ----
  var CF_KEY = 'hg_crew_filter';
  var cfCount = document.getElementById('cfCount');
  var cfBadge = document.getElementById('cfBadge');
  var crewFilter = document.getElementById('crewFilter');
  function setBadge(n){
    if(!cfBadge) return;
    if(n > 0){ cfBadge.textContent = n + (n === 1 ? ' geselecteerd' : ' geselecteerd'); cfBadge.hidden = false; }
    else { cfBadge.hidden = true; cfBadge.textContent = ''; }
  }
  // slug -> originele naam (uit de chips)
  var nameMap = {};
  var cfChips = Array.prototype.slice.call(document.querySelectorAll('.cf-chip'));
  cfChips.forEach(function(c){ nameMap[c.getAttribute('data-person')] = c.textContent.trim(); });

  function loadSel(){
    try{ var v = JSON.parse(localStorage.getItem(CF_KEY)); return Array.isArray(v) ? v : []; }
    catch(err){ return []; }
  }
  function saveSel(sel){
    try{ localStorage.setItem(CF_KEY, JSON.stringify(sel)); }catch(err){}
  }
  var cfSel = loadSel();

  function namesLabel(sel){
    var ns = sel.map(function(s){ return nameMap[s] || s; });
    if(ns.length === 1) return ns[0];
    if(ns.length === 2) return ns[0] + ' & ' + ns[1];
    return ns.slice(0, -1).join(', ') + ' & ' + ns[ns.length - 1];
  }

  function applyFilter(){
    var sel = cfSel;
    var rows = document.querySelectorAll('.ac-row[data-people]');
    var blocks = document.querySelectorAll('.crew-leg-block');
    var details = document.querySelectorAll('details.crew-details');
    var sections = document.querySelectorAll('section.day');

    // chip active-state
    cfChips.forEach(function(c){
      var on = sel.indexOf(c.getAttribute('data-person')) !== -1;
      c.classList.toggle('active', on);
    });
    // reset highlights + dimming
    document.querySelectorAll('.seat.person-hit').forEach(function(s){ s.classList.remove('person-hit'); });
    document.querySelectorAll('.seat.cf-dim').forEach(function(s){ s.classList.remove('cf-dim'); });

    if(!sel.length){
      // toon alles
      rows.forEach(function(r){ r.classList.remove('cf-hidden'); });
      blocks.forEach(function(b){ b.classList.remove('cf-hidden'); });
      sections.forEach(function(s){ s.classList.remove('cf-hidden'); });
      if(cfCount) cfCount.textContent = 'Toont alle vluchten';
      setBadge(0);
      return;
    }

    // rows tonen/verbergen op basis van overlap met de selectie
    rows.forEach(function(r){
      var people = (r.getAttribute('data-people') || '').split(/\s+/).filter(Boolean);
      var hit = sel.some(function(s){ return people.indexOf(s) !== -1; });
      r.classList.toggle('cf-hidden', !hit);
      if(hit){
        r.querySelectorAll('.seat[data-person]').forEach(function(seat){
          if(sel.indexOf(seat.getAttribute('data-person')) !== -1){ seat.classList.add('person-hit'); }
          else { seat.classList.add('cf-dim'); }
        });
      }
    });
    // leg-blocks: verberg als alle rows erin verborgen zijn
    blocks.forEach(function(b){
      var rs = b.querySelectorAll('.ac-row[data-people]');
      var anyVisible = Array.prototype.some.call(rs, function(r){ return !r.classList.contains('cf-hidden'); });
      b.classList.toggle('cf-hidden', !anyVisible);
    });
    // open alle zichtbare crew-details zodat de gefilterde vluchten meteen zichtbaar zijn
    details.forEach(function(d){
      var vis = d.querySelectorAll('.ac-row[data-people]:not(.cf-hidden)').length > 0;
      if(vis) d.open = true;
    });
    // day-sections: verberg een hele dag als die geen enkele zichtbare vlucht heeft
    var visCount = 0;
    sections.forEach(function(s){
      var vis = s.querySelectorAll('.ac-row[data-people]:not(.cf-hidden)').length;
      s.classList.toggle('cf-hidden', vis === 0);
    });
    visCount = document.querySelectorAll('.ac-row[data-people]:not(.cf-hidden)').length;

    if(cfCount){
      var noun = visCount === 1 ? 'vlucht' : 'vluchten';
      cfCount.innerHTML = '<b>' + visCount + '</b> ' + noun + ' met ' + namesLabel(sel);
    }
    setBadge(sel.length);
  }

  // chip-klik: toggle slug in/uit selectie
  cfChips.forEach(function(c){
    c.addEventListener('click', function(){
      var slug = c.getAttribute('data-person');
      var i = cfSel.indexOf(slug);
      if(i === -1){ cfSel.push(slug); } else { cfSel.splice(i, 1); }
      saveSel(cfSel);
      applyFilter();
    });
  });
  var cfReset = document.getElementById('cfReset');
  if(cfReset){
    cfReset.addEventListener('click', function(){
      cfSel = [];
      try{ localStorage.removeItem(CF_KEY); }catch(err){}
      applyFilter();
    });
  }
  // init: pas opgeslagen selectie toe; klap de filter open als er een actieve selectie is
  if(crewFilter && cfSel.length){ crewFilter.open = true; }
  applyFilter();
})();
"""

if __name__ == "__main__":
    main()
