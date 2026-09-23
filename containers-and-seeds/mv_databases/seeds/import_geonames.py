"""Construye el catálogo versionado desde los ZIP nacionales oficiales de GeoNames."""
import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

COUNTRIES = dict(AR='Argentina', BO='Bolivia', BR='Brasil', CL='Chile', CO='Colombia',
                 EC='Ecuador', GY='Guyana', PY='Paraguay', PE='Perú', SR='Suriname',
                 UY='Uruguay', VE='Venezuela', GF='French Guiana')
# Excluye barrios, lugares abandonados, históricos y asentamientos destruidos.
FEATURES = {'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLA5', 'PPLC'}


def build(directory, per_country=100):
    groups, sources = [], []
    for code, country in COUNTRIES.items():
        path = directory / f'smokecast-{code}.zip'
        with ZipFile(path) as archive:
            rows = csv.reader(io.StringIO(archive.read(f'{code}.txt').decode('utf-8')), delimiter='\t')
            candidates = [r for r in rows if r[6] == 'P' and r[7] in FEATURES and r[8] == code]
        candidates.sort(key=lambda r: (-int(r[14]), int(r[0])))
        selected, seen = [], set()
        for r in candidates:
            key = (r[1].casefold(), r[4], r[5])
            if key in seen or len(r[1]) > 120:
                continue
            seen.add(key)
            selected.append(dict(id=int(r[0]), name=r[1], country=country, country_code=code,
                                 latitude=float(r[4]), longitude=float(r[5]),
                                 population=int(r[14]) or None, feature_code=r[7],
                                 admin1=r[10], elevation_m=int(r[16]), modified=r[18]))
            if len(selected) == per_country:
                break
        if len(selected) < per_country:
            raise ValueError(f'{code}: solo {len(selected)} localidades elegibles')
        groups.append(selected)
        sources.append(dict(country_code=code, url=f'https://download.geonames.org/export/dump/{code}.zip',
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    # Intercalar países evita sesgar los primeros registros que muestran las APIs.
    cities = [city for row in zip(*groups) for city in row]
    return dict(source='GeoNames', license='CC BY 4.0',
                attribution='GeoNames — https://www.geonames.org/',
                retrieved_at=datetime.now(timezone.utc).isoformat(), sources=sources, cities=cities)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='directorio con smokecast-XX.zip')
    parser.add_argument('--per-country', type=int, default=100)
    args = parser.parse_args()
    catalog = build(args.directory, args.per_country)
    Path(__file__).with_name('cities_geonames.json').write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{len(catalog['cities'])} localidades verificables")
