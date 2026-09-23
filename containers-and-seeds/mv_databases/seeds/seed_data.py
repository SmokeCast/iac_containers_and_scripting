"""Carga datos sintéticos de SmokeCast bajo demanda."""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent
# seed_data.py vive en mv_databases/seeds; las credenciales están junto al Compose.
load_dotenv(ROOT.parent / ".env")
SEED_ID = "smokecast-faker-2026-09"
# Catálogo real compartido por ciudades, incendios y meteorología.
CATALOG = json.loads((ROOT / "cities_geonames.json").read_text(encoding="utf-8"))["cities"]
SENSITIVE_SITE_CATALOG = json.loads((ROOT / "sensitive_sites_catalog.json").read_text(encoding="utf-8"))
ACTIVE_CITIES = CATALOG
CATALOG_BY_ID = {c["id"]: c for c in CATALOG}
COUNTRY_GEOJSON_NAMES = {
    "Argentina": "Argentina", "Bolivia": "Bolivia", "Brasil": "Brazil", "Chile": "Chile",
    "Colombia": "Colombia", "Ecuador": "Ecuador", "Guyana": "Guyana", "Paraguay": "Paraguay",
    "Perú": "Peru", "Suriname": "Suriname", "Uruguay": "Uruguay", "Venezuela": "Venezuela",
    "French Guiana": "France",
}
POLYGONS = {}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=("all", "mysql", "postgres", "mongo"), default="all")
    parser.add_argument("--fires", type=int, default=100_000, help="detecciones para MySQL")
    parser.add_argument("--weather", type=int, default=100_000, help="lecturas para MongoDB")
    parser.add_argument("--cities", type=int, default=len(CATALOG), help="localidades únicas del catálogo (máximo 1300)")
    parser.add_argument("--sites", type=int, default=25_000, help="sitios sensibles para PostgreSQL")
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--replace-fires", action="store_true",
                        help="vacía fire_events/fire_detections antes de generar el dataset")
    parser.add_argument("--replace-cities", action="store_true",
                        help="vacía cities/sensitive_sites antes de generar el catálogo")
    options = parser.parse_args()
    if min(options.fires, options.weather, options.cities, options.sites) < 1:
        parser.error("las cantidades deben ser mayores que cero")
    if options.cities > len(CATALOG):
        parser.error(f"El catálogo tiene {len(CATALOG)} localidades únicas; no se duplican ciudades")
    if options.database == "all" and options.weather < options.cities:
        parser.error("--weather debe cubrir al menos una lectura por localidad")
    return options


def load_polygons():
    geojson_path = ROOT.parents[3] / "frontend-web" / "src" / "south-america.json"
    with geojson_path.open(encoding="utf-8") as file:
        geojson = json.load(file)
    for feature in geojson["features"]:
        name = feature.get("properties", {}).get("name")
        if name:
            POLYGONS[name] = shape(feature["geometry"])


def nearby_point(country, latitude, longitude, jitter=0.15):
    """Punto sintético cercano, validado en tierra del país del evento."""
    polygon = POLYGONS[COUNTRY_GEOJSON_NAMES[country]]
    for _ in range(2000):
        lat = round(latitude + random.uniform(-jitter, jitter), 6)
        lon = round(longitude + random.uniform(-jitter, jitter), 6)
        if polygon.contains(Point(lon, lat)):
            return lat, lon
    raise RuntimeError(f"No se encontró tierra cerca de {latitude}, {longitude} ({country})")


def seed_mysql(count, fake, replace_fires=False):
    import mysql.connector

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"), port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "db1_fire_catalog"),
    )
    cursor = connection.cursor()
    if replace_fires:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE fire_detections")
        cursor.execute("TRUNCATE TABLE fire_events")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # El mapa simplificado no incluye algunas islas reales; conservarlas en el
    # catálogo, pero no fabricar incendios allí sin un polígono de tierra.
    anchors = [c for c in ACTIVE_CITIES if POLYGONS[COUNTRY_GEOJSON_NAMES[c["country"]]].intersects(
        Point(c["longitude"], c["latitude"]).buffer(0.3))]
    if not anchors:
        raise ValueError("El mapa no cubre las localidades seleccionadas")
    event_count = max(1, min(5_000, count // 5))
    # Cobertura equilibrada para pruebas, no una distribución observada en la naturaleza.
    # Cada evento conserva un rango coherente en todas sus detecciones.
    intensity_ranges = ((8, 30), (30.01, 90), (90.01, 150), (150.01, 280))
    events, event_ids = [], []
    for index in range(event_count):
        anchor = anchors[index % len(anchors)]
        country = anchor["country"]
        latitude, longitude = nearby_point(country, anchor["latitude"], anchor["longitude"], 0.35)
        started = fake.date_time_between(start_date="-30d", end_date="-2h")
        event = (latitude, longitude, 0, 0, started,
                 min(datetime.now(), started + timedelta(hours=random.randint(1, 36))), country)
        cursor.execute(
            "INSERT INTO fire_events (centroid_lat,centroid_lon,max_frp,detection_count,first_detected_at,last_detected_at,country_hint) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            event)
        events.append(event)
        event_ids.append(cursor.lastrowid)

    detections = []
    for index in range(count):
        event_index = index % event_count
        event = events[event_index]
        lat, lon = nearby_point(event[6], event[0], event[1], 0.015)
        detected = event[4] + (event[5] - event[4]) * random.random()
        min_frp, max_frp = intensity_ranges[event_index % len(intensity_ranges)]
        detections.append((event_ids[event_index], lat, lon, round(random.uniform(280, 360), 2),
                           round(random.uniform(min_frp, max_frp), 2), random.choice(("low", "nominal", "high")),
                           detected.date(), detected.strftime("%H%M")))
    cursor.executemany(
        "INSERT INTO fire_detections (fire_event_id,latitude,longitude,brightness,frp,confidence,acq_date,acq_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        detections)
    # Los agregados del evento se calculan de sus detecciones, no al azar.
    grouped = [[] for _ in event_ids]
    for index, detection in enumerate(detections):
        grouped[index % event_count].append(detection)
    for event_id, rows in zip(event_ids, grouped):
        times = [datetime.combine(row[6], datetime.strptime(row[7], "%H%M").time()) for row in rows]
        cursor.execute(
            "UPDATE fire_events SET detection_count=%s, max_frp=%s, first_detected_at=%s, last_detected_at=%s WHERE id=%s",
            (len(rows), max(row[4] for row in rows), min(times), max(times), event_id))
    connection.commit()
    cursor.close(); connection.close()
    print(f"MySQL: {event_count:,} eventos y {count:,} detecciones cargados")


def seed_postgres(count, fake, replace_cities=False, sites_count=25_000):
    import psycopg2

    connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"), port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"), password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "db2_urban_exposure"))
    cursor = connection.cursor()
    if replace_cities:
        cursor.execute("TRUNCATE TABLE sensitive_sites, cities RESTART IDENTITY CASCADE")
    cities = [(c["id"], c["name"], c["country"], c["latitude"], c["longitude"], c["population"])
              for c in ACTIVE_CITIES[:count]]
    # GeoNames ID estable: reejecutar actualiza la localidad sin duplicarla.
    cursor.executemany("""INSERT INTO cities (id,name,country,latitude,longitude,population)
        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET
        name=EXCLUDED.name,country=EXCLUDED.country,latitude=EXCLUDED.latitude,
        longitude=EXCLUDED.longitude,population=EXCLUDED.population""", cities)
    cursor.execute("SELECT setval(pg_get_serial_sequence('cities', 'id'), GREATEST((SELECT MAX(id) FROM cities), 1))")
    # Primero se cargan referencias con nombre real verificable en capitales y
    # ciudades principales. No se asigna un hospital o colegio inventado a un
    # asentamiento remoto solo para completar el volumen del seed.
    city_by_key = {(c["country"], c["name"]): c for c in ACTIVE_CITIES}
    sites = []
    curated_keys = set()
    for item in SENSITIVE_SITE_CATALOG:
        city = city_by_key.get((item["country"], item["city"]))
        if city is None:
            continue
        sites.append((city["id"], item["name"][:150], item["type"]))
        curated_keys.add(city["id"])

    # El requisito de carga masiva se conserva con lugares sintéticos claramente
    # etiquetados, repartidos únicamente entre localidades urbanas (>= 50 mil
    # habitantes). Así no aparecen instituciones plausibles en la selva o en
    # zonas de alta montaña sin población urbana.
    urban_cities = [c for c in ACTIVE_CITIES if (c.get("population") or 0) >= 50_000]
    if not urban_cities:
        urban_cities = ACTIVE_CITIES[:]
    filler_types = (("hospital", "Centro de salud de referencia"),
                    ("clinic", "Centro de atención primaria"),
                    ("school", "Institución educativa municipal"),
                    ("university", "Campus universitario"),
                    ("fire_station", "Estación de bomberos"),
                    ("police_station", "Comisaría o estación policial"),
                    ("care_home", "Centro de atención y cuidado"),
                    ("shelter", "Albergue temporal"),
                    ("airport", "Terminal aéreo local"),
                    ("bus_terminal", "Terminal terrestre"),
                    ("port", "Instalación portuaria"),
                    ("power_station", "Subestación eléctrica"),
                    ("water_plant", "Planta de tratamiento de agua"),
                    ("market", "Mercado de abastos"),
                    ("industrial", "Zona industrial"),
                    ("reserve", "Área natural protegida"))
    filler_index = 0
    while len(sites) < sites_count:
        city = urban_cities[filler_index % len(urban_cities)]
        kind, label = filler_types[filler_index % len(filler_types)]
        sites.append((city["id"], f"{label} de {city['name']} · registro demo {filler_index + 1}"[:150], kind))
        filler_index += 1
    sites = sites[:sites_count]
    # Inserción por lotes para no mantener los 25 mil registros en memoria del driver.
    for index in range(0, len(sites), 1_000):
        batch = sites[index:index + 1_000]
        cursor.executemany("INSERT INTO sensitive_sites (city_id,name,type) VALUES (%s,%s,%s)", batch)
    connection.commit(); cursor.close(); connection.close()
    print(f"PostgreSQL: {count:,} ciudades y {sites_count:,} sitios sensibles cargados")



def weather_values(city_id, latitude, longitude, timestamp):
    """Modelo de demostración, no observaciones ni pronóstico meteorológico."""
    reference = CATALOG_BY_ID.get(city_id, {})
    elevation = max(0, reference.get("elevation_m", 0))
    local_hour = (timestamp.hour + longitude / 15) % 24
    day_cycle = math.cos(2 * math.pi * (local_hour - 14) / 24)
    season = math.cos(2 * math.pi * (timestamp.timetuple().tm_yday - 200) / 365.25)
    if latitude < 0:
        season *= -1
    temperature = (28 - abs(latitude) * 0.35 - elevation * 0.006
                   + season * min(10, abs(latitude) / 4) + 4 * day_cycle)
    # Variaciones continuas por ciudad/hora: evita saltos aleatorios extremos.
    phase = city_id % 360 * math.pi / 180
    wave = math.sin(timestamp.timestamp() / 3600 / 12 + phase)
    return dict(temperature_c=round(temperature + wave, 1),
                wind_speed_kmh=round(12 + 8 * wave, 1),
                wind_direction_deg=round(city_id % 360 + 20 * wave) % 360,
                pm25_ug_m3=round(8 + city_id % 35 + 5 * wave, 1),
                humidity_pct=round(max(15, min(98, 65 - 15 * day_cycle + 8 * wave))))


def seed_mongo(count, fake):
    from pymongo import MongoClient
    import psycopg2

    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                         username=os.getenv("MONGO_ROOT_USERNAME") or None,
                         password=os.getenv("MONGO_ROOT_PASSWORD") or None,
                         authSource=os.getenv("MONGO_AUTH_SOURCE", "admin"), serverSelectionTimeoutMS=5000)
    collection = client[os.getenv("MONGO_DB_NAME", "db3_atmosphere_feed")][os.getenv("MONGO_COLLECTION", "weather_readings")]
    # MS3 debe usar exactamente el catálogo de ciudades de MS2; generar nombres
    # y coordenadas de forma independiente rompe la relación city_id.
    city_connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"), port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"), password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "db2_urban_exposure"))
    city_cursor = city_connection.cursor()
    city_cursor.execute("SELECT id, name, country, latitude, longitude FROM cities ORDER BY id")
    cities = city_cursor.fetchall()
    city_cursor.close(); city_connection.close()
    if not cities:
        raise RuntimeError("MS2 no tiene ciudades; ejecuta primero --database postgres")
    if count < len(cities):
        raise ValueError("--weather debe ser al menos el número de ciudades de PostgreSQL")
    collection.delete_many({"seed_id": SEED_ID})
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    batch = []
    for index in range(count):
        city_id, city_name, country, latitude, longitude = cities[index % len(cities)]
        timestamp = start - timedelta(hours=index // len(cities))
        batch.append({"city_id": city_id, "city_name": city_name, "city_country": country,
                      "latitude": float(latitude), "longitude": float(longitude),
                      "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                      **weather_values(city_id, float(latitude), float(longitude), timestamp),
                      "seed_id": SEED_ID,
                      "source": "synthetic", "location_source": "MS2/GeoNames"})
        if len(batch) == 1_000:
            collection.insert_many(batch); batch.clear()
    if batch: collection.insert_many(batch)
    collection.create_index([("city_id", 1), ("timestamp", -1)])
    collection.create_index([("timestamp", -1)])
    client.close()
    print(f"MongoDB: {count:,} lecturas cargadas")


def main():
    global ACTIVE_CITIES
    options = parse_args()
    ACTIVE_CITIES = CATALOG[:options.cities]
    random.seed(options.seed)
    fake = Faker("es_ES"); fake.seed_instance(options.seed)
    load_polygons()
    if options.database in ("all", "postgres"): seed_postgres(options.cities, fake, options.replace_cities, options.sites)
    if options.database in ("all", "mysql"): seed_mysql(options.fires, fake, options.replace_fires)
    if options.database in ("all", "mongo"): seed_mongo(options.weather, fake)


if __name__ == "__main__":
    main()
