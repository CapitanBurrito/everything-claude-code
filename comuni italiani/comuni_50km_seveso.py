import requests
import math
import json

# Coordinate di Seveso (centro)
SEVESO_LAT = 45.6583
SEVESO_LON = 9.1583
RADIUS_KM = 50
RADIUS_M = RADIUS_KM * 1000

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

# Query Overpass: relation con boundary=administrative e admin_level=8
# (in Italia = comuni) + nodi place=city/town/village per classificare
# ciascun comune come "citta'" o "paese"
query = f"""
[out:json][timeout:300];
(
  relation["boundary"="administrative"]["admin_level"="8"](around:{RADIUS_M},{SEVESO_LAT},{SEVESO_LON});
  node["place"~"^(city|town|village)$"](around:{RADIUS_M},{SEVESO_LAT},{SEVESO_LON});
);
out center tags;
"""

print("Interrogo Overpass API (comuni + classificazione citta'/paese)...")
r = requests.post(OVERPASS_URL, data={"data": query}, timeout=320)
r.raise_for_status()
data = r.json()

PLACE_A_TIPO = {"city": "citta'", "town": "paese", "village": "paese"}

# Nodi place, indicizzati per nome: usati per stimare il tipo del comune
# quando la relation non porta un tag place proprio.
place_by_name = {}
for el in data.get("elements", []):
    if el.get("type") != "node":
        continue
    tags = el.get("tags", {})
    nome = tags.get("name")
    place = tags.get("place")
    if nome and place:
        place_by_name.setdefault(nome, place)

comuni = []
for el in data.get("elements", []):
    if el.get("type") != "relation":
        continue
    tags = el.get("tags", {})
    nome = tags.get("name")
    if not nome:
        continue

    # "out center" fornisce il centroide della relation
    center = el.get("center")
    if not center:
        continue

    lat = center["lat"]
    lon = center["lon"]
    # Distanza dal centro del bounding box: solo indicativa/per ordinamento.
    # Overpass ha gia' filtrato i comuni il cui confine reale rientra nei
    # RADIUS_M richiesti, quindi qui non si ri-filtra: il centro del bbox
    # puo' cadere oltre RADIUS_KM anche per comuni correttamente inclusi
    # (es. comuni allungati/irregolari), e ri-escluderli farebbe perdere
    # comuni validi.
    dist = haversine(SEVESO_LAT, SEVESO_LON, lat, lon)

    place = tags.get("place") or place_by_name.get(nome)
    tipo = PLACE_A_TIPO.get(place)

    comuni.append({
        "nome": nome,
        "lat": lat,
        "lon": lon,
        "distanza_km": round(dist, 2),
        "tipo": tipo,  # "citta'" / "paese" / None se non classificabile
        "istat": tags.get("ref:ISTAT"),
        "provincia": tags.get("addr:province") or tags.get("is_in:province"),
        "regione": tags.get("addr:region") or tags.get("is_in:region")
    })

comuni.sort(key=lambda x: x["distanza_km"])

print(f"\nTrovati {len(comuni)} comuni entro {RADIUS_KM} km da Seveso:\n")
for c in comuni:
    tipo = c["tipo"] or "n/d"
    print(f"{c['distanza_km']:>6.2f} km  {c['nome']:<30} ({tipo})")

with open("comuni_50km_seveso.json", "w", encoding="utf-8") as f:
    json.dump(comuni, f, ensure_ascii=False, indent=2)

print(f"\nSalvato in comuni_50km_seveso.json ({len(comuni)} comuni)")
