#!/usr/bin/env python3
"""Build index.html for The Highland Games travel diary from journal.json."""
import json
import html
import os
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


def role_badge(role):
    cls = {
        "PIC": "pic",
        "COPILOT": "copilot",
        "PAX 1": "pax",
        "PAX 2": "pax",
    }.get(role, "pax")
    label = {"PIC": "PIC ✈️", "COPILOT": "Copilot", "PAX 1": "Passagier", "PAX 2": "Passagier"}.get(role, role)
    return f'<span class="role {cls}">{html.escape(label)}</span>'


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
    """An entry: {type: 'photo'|'note', text, photos:[{file,caption}], time}"""
    parts = []
    t = entry.get("time", "")
    text = entry.get("text", "")
    photos = entry.get("photos", [])
    parts.append('<div class="entry">')
    if t:
        parts.append(f'<div class="entry-time">{html.escape(t)}</div>')
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


def render_day(data, day):
    ap = data["airports"]
    parts = []
    rest = day.get("restDay")
    parts.append(f'<section class="day{" rest" if rest else ""}" id="{day["date"]}">')
    parts.append('<div class="day-head">')
    parts.append(f'<div class="day-date"><span class="wd">{html.escape(day["weekday"])}</span><span class="dt">{html.escape(day["date"][8:10])}/{html.escape(day["date"][5:7])}</span></div>')
    parts.append(f'<h2>{html.escape(day["label"])}</h2>')
    parts.append('</div>')

    if rest:
        parts.append('<div class="rest-banner">🛌 Rustdag — geen vluchten gepland. Tijd om de Highlands te proeven.</div>')
    else:
        # legs
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
            ew = leg.get("ewoud")
            ewa = leg.get("ewoud_aircraft", "")
            parts.append(
                f'<div class="leg-meta">{meta}'
                + (f' · {role_badge(ew)} <span class="ac">{html.escape(ewa)}</span>' if ew else "")
                + '</div>'
            )
            parts.append('</div>')
        parts.append('</div>')

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

    days_html = "\n".join(render_day(data, d) for d in data["days"])

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

  {days_html}
</main>

<footer>
  <p>✈️ The Highland Games · Fly-Out 2026 · gemaakt door Koda 🐾</p>
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
.legs{display:grid;gap:10px;margin-bottom:6px}
.leg{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);
  border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.leg-route{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.apt{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:.04em;color:var(--accent)}
.apt-name{font-size:13px;color:var(--muted)}
.arrow{color:var(--accent2);font-size:18px;margin:0 2px}
.leg-meta{font-size:13px;color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.role{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
.role.pic{background:rgba(72,169,255,.18);color:var(--pic)}
.role.copilot{background:rgba(126,224,192,.18);color:var(--copilot)}
.role.pax{background:rgba(185,167,255,.18);color:var(--pax)}
.ac{font-family:'Bebas Neue',sans-serif;letter-spacing:.05em;color:var(--ink);font-size:15px}
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
})();
"""

if __name__ == "__main__":
    main()
