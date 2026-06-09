import io

src = open("build.py", encoding="utf-8").read()
if "def render_prep_section" in src:
    print("Functie bestaat al, sla over.")
else:
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
        "\n"
    )
    marker = "\ndef render_day(data, day):"
    if marker not in src:
        raise SystemExit("MARKER NIET GEVONDEN")
    src = src.replace(marker, func + marker, 1)
    open("build.py", "w", encoding="utf-8").write(src)
    print("Functie toegevoegd.")
