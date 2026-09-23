# Seeder de SmokeCast

Carga datos ficticios y localidades reales en las bases de datos de MS1, MS2 y
MS3. Es un proceso puntual: termina cuando finaliza la carga. Las tablas y
colecciones las crean los microservicios; el seeder solo inserta datos.

## Requisitos

- Docker y Docker Compose, o Python 3.13+ para ejecutarlo directamente.
- Las bases levantadas en la red externa `smokecast_db_network`.
- Un `.env` con las credenciales de `mv_databases`.

## Ejecutar con Python

Desde esta carpeta:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python seed_data.py --database all --fires 100000 --weather 100000 --sites 25000 --replace-fires --replace-cities
```

El script lee las credenciales desde `../.env`. Los flags `--replace-fires` y
`--replace-cities` eliminan los datos generados anteriormente antes de insertar
los nuevos. Úsalos solo cuando quieras regenerar esos datos.

## Ejecutar como contenedor

Primero levanta las bases desde `mv_databases`:

```bash
cd ..
docker compose up -d
cd seeds
docker compose --env-file ../.env build
docker compose --env-file ../.env run --rm seed
```

También puedes cambiar cantidades sin editar el Compose:

```bash
SEED_FIRES=100000 SEED_WEATHER=100000 SEED_SITES=25000 \
docker compose --env-file ../.env run --rm seed
```

El Compose usa los servicios `mysql_db`, `postgres_db` y `mongo_db` de la red
`smokecast_db_network`. Si las bases están en otra máquina, configura sus IP
privadas en el entorno del contenedor.

## Publicar la imagen

Construye la imagen con una etiqueta de versión y publícala en Docker Hub:

```bash
cd ../../../../
docker login
docker build \
  -f iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/Dockerfile \
  --build-arg VERSION=v1.0.0 \
  -t empuiquin24/smokecast-seed:v1.0.0 .
docker push empuiquin24/smokecast-seed:v1.0.0
```

En la MV de bases define en `.env`:

```env
SEED_IMAGE=empuiquin24/smokecast-seed
SEED_IMAGE_TAG=v1.0.0
```

Después descarga y ejecuta la versión indicada:

```bash
docker compose --env-file ../.env pull
docker compose --env-file ../.env run --rm seed
```

## Datos generados

| Servicio | Datos |
|---|---|
| MS1 / MySQL | Eventos y detecciones de incendios |
| MS2 / PostgreSQL | Localidades y sitios sensibles |
| MS3 / MongoDB | Lecturas meteorológicas por localidad |

Los valores meteorológicos y las detecciones son sintéticos para pruebas. Las
localidades provienen del catálogo GeoNames incluido en `cities_geonames.json`.

Parámetros principales: `--database`, `--fires`, `--weather`, `--cities`,
`--sites`, `--replace-fires` y `--replace-cities`.
