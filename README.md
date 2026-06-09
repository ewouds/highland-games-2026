# ✈️ The Highland Games — Live Reisverslag (Fly-Out 2026)

**Live site:** https://ewouds.github.io/highland-games-2026/
**Repo:** ewouds/highland-games-2026 (GitHub Pages, branch `main`, root)
**Telegram:** Koda-Hub groep (`-1003835115929`), topic **4871** "✈️ The Highland Games"
**Reis:** wo 10/6 → ma 15/6 2026, RAAC fly-out Antwerpen → Schotland → Ierland → thuis
**Rustdag:** za 13/6 (geen vluchten)

## Hoe het werkt
Ewoud dropt onderweg foto's + tekst (meestal in topic 4871, soms DM). Koda zet elke drop om in
een journal-entry, regenereert de HTML en pusht naar GitHub Pages. De pagina is direct deelbaar.

## Bestanden
- `journal.json` — **bron van waarheid**: meta, vliegtuigen, vlieghavens, dagen, legs, entries
- `build.py` — genereert `index.html` uit journal.json (Leaflet-kaart, timeline, foto-galerij, lightbox)
- `add_update.py` — voegt entry toe (tekst/foto's), kopieert foto's, build + git push
- `photos/` — alle foto's (worden mee gepusht)
- `crew-reference.md` — volledige crew/routing uit de PDF + Ewoud's persoonlijke schema
- `index.html` — gegenereerd (niet handmatig editen)

## Update toevoegen (de normale flow)
```bash
cd /home/node/workspace/highland-games

# tekst + 1 of meer foto's voor vandaag (datum auto = trip-dag in CEST)
python3 add_update.py --date today --time "14:30" \
  --text "Geland op Barra, strandbaan! Wind recht op de neus." \
  --photo /pad/naar/foto1.jpg "Touchdown op het strand" \
  --photo /pad/naar/foto2.jpg "OO-MAV op het zand"

# enkel tekst
python3 add_update.py --date 2026-06-11 --text "Avondeten in Inverness 🏴"

# alleen herbouwen + pushen (na handmatige journal-edit)
python3 add_update.py --rebuild
```
- `--date` accepteert `today` of `2026-06-1X` (alleen 10–15 juni geldig).
- Foto-paden: gebruik de gedownloade media-paden van Telegram (file_fetch levert een lokaal pad).
- Het script doet automatisch `git pull --rebase` → edit → `build.py` → commit → push (token uit Azure KV `github-token`).

## Workflow per inkomende Telegram-update (voor de agent)
1. Foto('s) ophalen → lokaal pad (media is al als pad beschikbaar in de message, anders file_fetch).
2. Korte, mooie bijschriften maken (NL, sfeervol, kort). Tekst = wat Ewoud schreef, evt. licht opgepoetst.
3. `add_update.py` draaien met juiste `--date` (meestal `today`), `--time` (HH:MM CEST), `--text`, `--photo ...`.
4. Bevestigen in het topic: korte reactie + de live link.
5. Opslaan in OV indpassend (mijlpalen, niet elke foto).

## Aandachtspunten
- **Croppen niet nodig** zoals bij aquarium — vliegfoto's mogen full-frame.
- Grote foto's: prima, maar als een foto >5 MB is overweeg `Pillow` resize naar max 2000px breed voor snelle laadtijd.
- Token staat in KV (`github-token`, scope `repo`, login `ewouds`) — nooit hardcoden.
- Bij merge-conflict op push: het script doet pull --rebase; bij echte conflicten handmatig oplossen in journal.json.
