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

# Query Overpass: solo relation con boundary=administrative e admin_level=8
# In Italia admin_level=8 = comuni
query = f"""
[out:json][timeout:300];
(
  relation["boundary"="administrative"]["admin_level"="8"](around:{RADIUS_M},{SEVESO_LAT},{SEVESO_LON});
);
out center tags;
"""

print("Interrogo Overpass API (solo comuni ufficiali)...")
r = requests.post(OVERPASS_URL, data={"data": query}, timeout=320)
r.raise_for_status()
data = r.json()

comuni = []
for el in data.get("elements", []):
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

    comuni.append({
        "nome": nome,
        "lat": lat,
        "lon": lon,
        "distanza_km": round(dist, 2),
        "istat": tags.get("ref:ISTAT"),
        "provincia": tags.get("addr:province") or tags.get("is_in:province"),
        "regione": tags.get("addr:region") or tags.get("is_in:region")
    })

comuni.sort(key=lambda x: x["distanza_km"])

print(f"\nTrovati {len(comuni)} comuni entro {RADIUS_KM} km da Seveso:\n")
for c in comuni:
    print(f"{c['distanza_km']:>6.2f} km  {c['nome']}")

with open("comuni_50km_seveso.json", "w", encoding="utf-8") as f:
    json.dump(comuni, f, ensure_ascii=False, indent=2)

print(f"\nSalvato in comuni_50km_seveso.json ({len(comuni)} comuni)")
