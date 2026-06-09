#!/usr/bin/env python3
# One-shot fixer: add render_prep_section + CSS, then we build.
import io, sys

p = "build.py"
src = open(p, encoding="utf-8").read()

# 1) Insert function before render_day
if "def render_prep_section" not in src:
    func = (
        "\n\n"
        "def render_prep_section(prep_days):\n"
        '    """Render all preparation days bundled into one collapsible section."""\n'
        "    if not prep_days:\n"
        '        return ""\n'
        '    days = sorted(prep_days, key=lambda d: d.get("date", ""))\n'
        "    parts = []\n"
        "    parts.append('<section class=\"day prep prep-section\" id=\"voorbereiding\">')\n"
        "    parts.append('<details class=\"prep-collapse\">')\n"
        "    parts.append(\n"
        "        '<summary><span class=\"prep-ico\">\U0001F4DD</span> Voorbereiding '\n"
        "        f'<span class=\"prep-count\">{len(days)} momenten</span>'\n"
        "        '<span class=\"sum-hint\">(klik om te tonen)</span></summary>'\n"
        "    )\n"
        "    parts.append('<div class=\"prep-body\">')\n"
        "    for day in days:\n"
        "        dt = f'{day[\"date\"][8:10]}/{day[\"date\"][5:7]}'\n"
        "        parts.append('<div class=\"prep-item\">')\n"
        "        parts.append(\n"
        "            f'<div class=\"prep-item-head\"><span class=\"prep-date\">{html.escape(dt)}</span>'\n"
        "            f'<span class=\"prep-label\">{html.escape(day.get(\"label\", \"\"))}</span></div>'\n"
        "        )\n"
        '        entries = day.get("entries", [])\n'
        "        if entries:\n"
        "            for e in entries:\n"
        "                parts.append(render_entry(e))\n"
        "        else:\n"
        "            parts.append('<div class=\"entries empty\">Nog geen updates.</div>')\n"
        "        parts.append('</div>')\n"
        "    parts.append('</div>')\n"
        "    parts.append('</details>')\n"
        "    parts.append('</section>')\n"
        '    return "\\n".join(parts)\n'
    )
    marker = "\ndef render_day(data, day):"
    if marker not in src:
        sys.exit("MARKER render_day NIET GEVONDEN")
    src = src.replace(marker, func + marker, 1)
    print("OK: functie ingevoegd")
else:
    print("skip: functie bestond al")

# 2) Add CSS for the prep collapse, anchored after .prep-banner rule
if ".prep-collapse" not in src:
    anchor = ".prep-banner{background:rgba(126,224,192,.08);border:1px dashed rgba(126,224,192,.4);\n  border-radius:12px;padding:14px 16px;color:var(--accent2);font-weight:500}"
    css = (
        anchor + "\n"
        ".prep-section{padding:0;overflow:hidden}\n"
        ".prep-collapse summary{cursor:pointer;list-style:none;padding:16px 18px;font-size:16px;font-weight:700;\n"
        "  color:var(--accent2);display:flex;align-items:center;gap:9px;user-select:none}\n"
        ".prep-collapse summary::-webkit-details-marker{display:none}\n"
        ".prep-collapse summary:hover{background:rgba(126,224,192,.06)}\n"
        ".prep-ico{font-size:17px}\n"
        ".prep-count{background:rgba(126,224,192,.16);color:var(--accent2);font-size:12px;font-weight:600;\n"
        "  padding:2px 9px;border-radius:999px}\n"
        ".prep-collapse[open] summary{border-bottom:1px solid rgba(126,224,192,.18)}\n"
        ".prep-collapse[open] .sum-hint::after{content:\"\u25B2\"}\n"
        ".prep-collapse:not([open]) .sum-hint::after{content:\"\u25BC\"}\n"
        ".prep-body{padding:6px 18px 18px}\n"
        ".prep-item{padding:14px 0;border-top:1px solid rgba(255,255,255,.06)}\n"
        ".prep-item:first-child{border-top:none}\n"
        ".prep-item-head{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}\n"
        ".prep-date{font-family:'Bebas Neue',sans-serif;letter-spacing:.05em;color:var(--accent);font-size:20px}\n"
        ".prep-label{font-weight:600;color:var(--ink);font-size:15px}\n"
    )
    if anchor not in src:
        sys.exit("CSS-anchor .prep-banner NIET GEVONDEN")
    src = src.replace(anchor, css, 1)
    print("OK: CSS ingevoegd")
else:
    print("skip: CSS bestond al")

open(p, "w", encoding="utf-8").write(src)

import ast
ast.parse(open(p, encoding="utf-8").read())
print("OK: build.py syntax geldig")
