"""Carga datos sintéticos de SmokeCast bajo demanda."""
from __future__ import annotations

import argparse
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "databases" / ".env")
SEED_ID = "smokecast-faker-2026-09"
COUNTRIES = [
    ("Perú", -18.35, -68.65, -0.04, -81.35),
    ("Brasil", -33.75, -34.80, 5.27, -73.99),
    ("Bolivia", -22.90, -57.45, -9.68, -69.64),
    ("Ecuador", -5.01, -75.19, 1.68, -81.08),
    ("Colombia", -4.23, -66.85, 12.46, -79.02),
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=("all", "mysql", "postgres", "mongo"), default="all")
    parser.add_argument("--fires", type=int, default=25_000, help="detecciones para MySQL")
    parser.add_argument("--weather", type=int, default=25_000, help="lecturas para MongoDB")
    parser.add_argument("--cities", type=int, default=25, help="ciudades para PostgreSQL")
    parser.add_argument("--seed", type=int, default=20260920)
    options = parser.parse_args()
    if min(options.fires, options.weather, options.cities) < 1:
        parser.error("las cantidades deben ser mayores que cero")
    return options


def random_bounds():
    return random.choice(COUNTRIES)


def ensure_mysql_column(cursor, table, column, definition):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
        (table, column),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def seed_mysql(count, fake):
    import mysql.connector

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"), port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "db1_fire_catalog"),
    )
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fire_events (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            centroid_lat DECIMAL(9,6), centroid_lon DECIMAL(9,6), max_frp DECIMAL(8,2),
            detection_count INT, first_detected_at DATETIME, last_detected_at DATETIME,
            country_hint VARCHAR(80), seed_id VARCHAR(80), INDEX idx_fire_events_seed (seed_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fire_detections (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, fire_event_id BIGINT NOT NULL,
            latitude DECIMAL(9,6), longitude DECIMAL(9,6), brightness DECIMAL(8,2),
            frp DECIMAL(8,2), confidence VARCHAR(10), acq_date DATE, acq_time VARCHAR(4),
            seed_id VARCHAR(80), CONSTRAINT fk_seed_event FOREIGN KEY (fire_event_id) REFERENCES fire_events(id),
            INDEX idx_fire_detections_seed (seed_id)
        )
    """)
    ensure_mysql_column(cursor, "fire_events", "seed_id", "VARCHAR(80)")
    ensure_mysql_column(cursor, "fire_detections", "seed_id", "VARCHAR(80)")
    cursor.execute("DELETE FROM fire_detections WHERE seed_id = %s", (SEED_ID,))
    cursor.execute("DELETE FROM fire_events WHERE seed_id = %s", (SEED_ID,))
    event_count = max(1, min(5_000, count // 5))
    events = []
    for _ in range(event_count):
        country, lat_min, lon_min, lat_max, lon_max = random_bounds()
        started = fake.date_time_between(start_date="-30d", end_date="-2h")
        events.append((random.uniform(lat_min, lat_max), random.uniform(lon_min, lon_max),
                       round(random.uniform(15, 280), 2), 0, started,
                       started + timedelta(hours=random.randint(1, 36)), country, SEED_ID))
    cursor.executemany(
        "INSERT INTO fire_events (centroid_lat,centroid_lon,max_frp,detection_count,first_detected_at,last_detected_at,country_hint,seed_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        events)
    cursor.execute("SELECT id FROM fire_events WHERE seed_id = %s ORDER BY id", (SEED_ID,))
    event_ids = [row[0] for row in cursor.fetchall()]
    counts = [0] * event_count
    detections = []
    for index in range(count):
        event_index = index % event_count
        counts[event_index] += 1
        event = events[event_index]
        detections.append((event_ids[event_index], event[0] + random.uniform(-.15, .15),
                            event[1] + random.uniform(-.15, .15), round(random.uniform(280, 360), 2),
                            round(random.uniform(8, 280), 2), random.choice(("low", "nominal", "high")),
                            fake.date_between(start_date="-30d", end_date="today"),
                            f"{random.randrange(0, 2400):04d}", SEED_ID))
    cursor.executemany(
        "INSERT INTO fire_detections (fire_event_id,latitude,longitude,brightness,frp,confidence,acq_date,acq_time,seed_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        detections)
    for event_id, amount in zip(event_ids, counts):
        cursor.execute("UPDATE fire_events SET detection_count = %s WHERE id = %s", (amount, event_id))
    connection.commit()
    cursor.close(); connection.close()
    print(f"MySQL: {event_count:,} eventos y {count:,} detecciones cargados")


def seed_postgres(count, fake):
    import psycopg2

    connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"), port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"), password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "db2_urban_exposure"))
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, country VARCHAR(80),
            latitude NUMERIC(9,6) NOT NULL, longitude NUMERIC(9,6) NOT NULL,
            population INTEGER, seed_id VARCHAR(80)
        );
        CREATE TABLE IF NOT EXISTS sensitive_sites (
            id SERIAL PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
            name VARCHAR(150), type VARCHAR(40)
        );
    """)
    cursor.execute("ALTER TABLE cities ADD COLUMN IF NOT EXISTS seed_id VARCHAR(80)")
    cursor.execute("DELETE FROM sensitive_sites WHERE city_id IN (SELECT id FROM cities WHERE seed_id = %s)", (SEED_ID,))
    cursor.execute("DELETE FROM cities WHERE seed_id = %s", (SEED_ID,))
    cities = []
    for _ in range(count):
        country, lat_min, lon_min, lat_max, lon_max = random_bounds()
        cities.append((fake.city(), country, round(random.uniform(lat_min, lat_max), 6),
                       round(random.uniform(lon_min, lon_max), 6), random.randint(20_000, 12_000_000), SEED_ID))
    cursor.executemany("INSERT INTO cities (name,country,latitude,longitude,population,seed_id) VALUES (%s,%s,%s,%s,%s,%s)", cities)
    cursor.execute("SELECT setval(pg_get_serial_sequence('cities', 'id'), GREATEST((SELECT MAX(id) FROM cities), 1))")
    connection.commit(); cursor.close(); connection.close()
    print(f"PostgreSQL: {count:,} ciudades cargadas")


def seed_mongo(count, fake):
    from pymongo import MongoClient

    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
                         username=os.getenv("MONGO_ROOT_USERNAME") or None,
                         password=os.getenv("MONGO_ROOT_PASSWORD") or None,
                         authSource=os.getenv("MONGO_AUTH_SOURCE", "admin"), serverSelectionTimeoutMS=5000)
    collection = client[os.getenv("MONGO_DB_NAME", "db3_atmosphere_feed")][os.getenv("MONGO_COLLECTION", "weather_readings")]
    collection.delete_many({"seed_id": SEED_ID})
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    batch = []
    for index in range(count):
        city_id = index % 25 + 1
        country, lat_min, lon_min, lat_max, lon_max = COUNTRIES[index % len(COUNTRIES)]
        batch.append({"city_id": city_id, "city_name": fake.city(), "city_country": country,
                      "latitude": round(random.uniform(lat_min, lat_max), 6),
                      "longitude": round(random.uniform(lon_min, lon_max), 6),
                      "timestamp": (start - timedelta(hours=index % 720)).isoformat().replace("+00:00", "Z"),
                      "temperature_c": round(random.uniform(8, 36), 1),
                      "wind_speed_kmh": round(random.uniform(0, 45), 1),
                      "wind_direction_deg": random.randrange(0, 360),
                      "pm25_ug_m3": round(random.uniform(5, 180), 1),
                      "humidity_pct": random.randrange(25, 96), "seed_id": SEED_ID})
        if len(batch) == 1_000:
            collection.insert_many(batch); batch.clear()
    if batch: collection.insert_many(batch)
    collection.create_index([("city_id", 1), ("timestamp", -1)])
    collection.create_index([("timestamp", -1)])
    client.close()
    print(f"MongoDB: {count:,} lecturas cargadas")


def main():
    options = parse_args()
    random.seed(options.seed)
    fake = Faker("es_ES"); fake.seed_instance(options.seed)
    if options.database in ("all", "mysql"): seed_mysql(options.fires, fake)
    if options.database in ("all", "postgres"): seed_postgres(options.cities, fake)
    if options.database in ("all", "mongo"): seed_mongo(options.weather, fake)


if __name__ == "__main__":
    main()
