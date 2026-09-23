"""Comprueba identidad geográfica y consistencia sin escribir en bases de datos."""
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import seed_data as seed


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed.load_polygons()

    def test_coverage_unique_ids_and_coordinates(self):
        self.assertEqual(set(Counter(c['country'] for c in seed.CATALOG).values()), {100})
        self.assertEqual(len({c['id'] for c in seed.CATALOG}), 1300)
        for c in seed.CATALOG:
            self.assertTrue(-90 <= c['latitude'] <= 90)
            self.assertTrue(-180 <= c['longitude'] <= 180)
            self.assertTrue(c['population'] is None or c['population'] > 0)

    def test_postgres_preserves_source_without_jitter(self):
        connection = MagicMock()
        with patch('psycopg2.connect', return_value=connection):
            seed.seed_postgres(1300, None)
        rows = connection.cursor.return_value.executemany.call_args_list[0].args[1]
        for row, city in zip(rows, seed.CATALOG):
            self.assertEqual(row, tuple(city[k] for k in ('id', 'name', 'country', 'latitude', 'longitude', 'population')))

    def test_every_mainland_anchor_can_generate_valid_fire(self):
        for c in seed.CATALOG:
            polygon = seed.POLYGONS[seed.COUNTRY_GEOJSON_NAMES[c['country']]]
            if not polygon.intersects(seed.Point(c['longitude'], c['latitude']).buffer(.3)):
                continue
            lat, lon = seed.nearby_point(c['country'], c['latitude'], c['longitude'], .35)
            self.assertTrue(polygon.contains(seed.Point(lon, lat)))
            dlat, dlon = seed.nearby_point(c['country'], lat, lon, .015)
            self.assertTrue(polygon.contains(seed.Point(dlon, dlat)))

    def test_70000_detections_match_event_aggregates(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        events, updates = {}, {}
        def execute(query, args):
            if query.startswith('INSERT INTO fire_events'):
                cursor.lastrowid = len(events) + 1
                events[cursor.lastrowid] = args
            elif query.startswith('UPDATE fire_events'):
                updates[args[-1]] = args
        cursor.execute.side_effect = execute
        with patch('mysql.connector.connect', return_value=connection):
            seed.seed_mysql(70000, seed.Faker())
        rows = cursor.executemany.call_args.args[1]
        self.assertEqual(len(rows), 70000)
        grouped = {}
        for row in rows:
            grouped.setdefault(row[0], []).append(row)
            event = events[row[0]]
            polygon = seed.POLYGONS[seed.COUNTRY_GEOJSON_NAMES[event[6]]]
            self.assertTrue(polygon.contains(seed.Point(row[2], row[1])))
            self.assertLessEqual(abs(row[1] - event[0]), .015001)
            self.assertLessEqual(abs(row[2] - event[1]), .015001)
        for event_id, detections in grouped.items():
            times = [datetime.combine(r[6], datetime.strptime(r[7], '%H%M').time()) for r in detections]
            self.assertEqual(updates[event_id][:4],
                             (len(detections), max(r[4] for r in detections), min(times), max(times)))
        levels = Counter('Crítico' if r[1] > 150 else 'Alto' if r[1] > 90
                         else 'Moderado' if r[1] > 30 else 'Bajo' for r in updates.values())
        self.assertEqual(levels, dict(Bajo=1250, Moderado=1250, Alto=1250, Crítico=1250))

    def test_weather_uses_postgres_identity_and_unique_hourly_timestamps(self):
        cities = [(c['id'], c['name'], c['country'], c['latitude'], c['longitude']) for c in seed.CATALOG]
        connection = MagicMock()
        connection.cursor.return_value.fetchall.return_value = cities
        client = MagicMock()
        collection = client.__getitem__.return_value.__getitem__.return_value
        inserted = []
        collection.insert_many.side_effect = lambda batch: inserted.extend(batch.copy())
        with patch('psycopg2.connect', return_value=connection), patch('pymongo.MongoClient', return_value=client):
            seed.seed_mongo(70000, None)
        self.assertEqual(len(inserted), 70000)
        self.assertEqual(len({(r['city_id'], r['timestamp']) for r in inserted}), 70000)
        self.assertEqual(len({r['city_id'] for r in inserted}), 1300)
        for r in inserted:
            city = seed.CATALOG_BY_ID[r['city_id']]
            self.assertEqual((r['city_name'], r['city_country'], r['latitude'], r['longitude']),
                             (city['name'], city['country'], city['latitude'], city['longitude']))
            self.assertEqual(r['source'], 'synthetic')
            self.assertTrue(0 <= r['humidity_pct'] <= 100)
            self.assertTrue(0 <= r['wind_direction_deg'] < 360)


if __name__ == '__main__':
    unittest.main()
