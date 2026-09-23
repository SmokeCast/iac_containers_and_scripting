# Microservicios en Docker

Las imágenes se publican en Docker Hub bajo el usuario `empuiquin24` y el
Compose las consume desde `docker-compose.yml`.

## Publicar imágenes

Desde la raíz del proyecto:

```bash
docker login
docker build -t empuiquin24/smokecast-ms1-fire-catalog:latest ./ms1-fire-catalog
docker build -t empuiquin24/smokecast-ms2-urban-exposure:latest ./ms2-urban-exposure
docker build -t empuiquin24/smokecast-ms3-atmosphere-feed:latest ./ms3-atmosphere-feed
docker build -t empuiquin24/smokecast-ms4-smoke-brain:latest ./ms4-smoke-brain
docker build -t empuiquin24/smokecast-ms5-analytics-gateway:latest ./ms5-analytics-gateway

docker push empuiquin24/smokecast-ms1-fire-catalog:latest
docker push empuiquin24/smokecast-ms2-urban-exposure:latest
docker push empuiquin24/smokecast-ms3-atmosphere-feed:latest
docker push empuiquin24/smokecast-ms4-smoke-brain:latest
docker push empuiquin24/smokecast-ms5-analytics-gateway:latest
```

## Arrancar

Primero crea las bases con el Compose de `mv_databases`.
Después, en esta carpeta:

```bash
cp env.example .env
# Completa las credenciales reales en .env
docker compose pull
docker compose up -d
```

Este Compose crea únicamente su red Docker local. Las bases de datos pueden vivir
en otra máquina virtual: configura `MYSQL_HOST`, `POSTGRES_HOST` y `MONGO_HOST`
con sus IP privadas o DNS privado. Para microservicios distribuidos en máquinas
distintas, reemplaza `MS1_URL`, `MS2_URL` y `MS3_URL` por sus direcciones privadas.
No incluye las bases de datos ni ejecuta el seed.

## API Gateway y Swagger

En ejecución local deja `MS1_PUBLIC_BASE_PATH` hasta `MS5_PUBLIC_BASE_PATH` en
`/`. Si API Gateway publica las APIs con los prefijos `/ms1` a `/ms5`, cambia
los valores correspondientes en `.env`:

```env
MS1_PUBLIC_BASE_PATH=/ms1
MS2_PUBLIC_BASE_PATH=/ms2
MS3_PUBLIC_BASE_PATH=/ms3
MS4_PUBLIC_BASE_PATH=/ms4
MS5_PUBLIC_BASE_PATH=/ms5
```

Así Swagger funcionará desde `/msN/docs` y sus botones **Try it out** usarán
automáticamente el prefijo público correcto.
