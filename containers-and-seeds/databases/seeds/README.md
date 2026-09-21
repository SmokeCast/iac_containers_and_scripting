# Seeds de desarrollo

Docker Compose solo levanta las bases. Los datos sintéticos se cargan explícitamente
con [`seed_data.py`](seed_data.py), por lo que el arranque de la infraestructura no
borra ni modifica datos existentes.

```bash
cd cloud-formation-iac/containers-and-seeds
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_data.py --database all
```

El comando anterior crea 25 000 detecciones en MySQL, 25 ciudades en PostgreSQL y
25 000 lecturas meteorológicas en MongoDB. También puedes ejecutar una sola base:

```bash
python seed_data.py --database mysql --fires 25000
python seed_data.py --database mongo --weather 25000
python seed_data.py --database postgres --cities 100
```

El script lee `databases/.env`, usa una semilla aleatoria fija y solo reemplaza sus
propios registros mediante `seed_id`.
