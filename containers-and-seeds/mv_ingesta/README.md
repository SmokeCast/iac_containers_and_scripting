# MV de ingesta

Esta carpeta contiene el Compose y las variables de la MV de ingesta. El
Compose usa imágenes publicadas en Docker Hub; el código fuente y los
Dockerfiles están en [data-ingestion](../../../data-ingestion/).

## Preparación

Desde esta carpeta:

```bash
cp env.example .env
docker compose pull
```

Completa en `.env` los hosts privados de las bases de datos, el bucket S3 y
la etiqueta de imagen. Si la MV usa un rol IAM como `LabRole`, deja vacías
las variables de credenciales AWS.

Para probar la ingesta manualmente:

```bash
./run-ingestion.sh
```

El script ejecuta los tres workers en orden. Cada worker termina al completar
su carga en S3.

## Programar la ingesta con cron

• **Paso 1:** En la **MV de ingesta**, ejecuta:

```bash
sudo crontab -e
```

• **Paso 2:** Agrega esta línea al final del archivo para ejecutar la ingesta
todos los días a las 02:00:

```cron
0 2 * * * /home/ubuntu/automatizar/run-ingestion.sh >> /home/ubuntu/smokecast-ingesta.log 2>&1
```

Cambia la ruta si guardaste el proyecto en otra carpeta. El script incluido es
`containers-and-seeds/mv_ingesta/run-ingestion.sh`.

• **Paso 3:** Guarda el archivo y reinicia la MV:

```bash
sudo reboot
```

Después ingresa nuevamente por SSH y revisa la ejecución:

```bash
docker ps -a
tail -n 100 /home/ubuntu/smokecast-ingesta.log
```

Como los workers son procesos puntuales, aparecerán como contenedores
`Exited (0)` después de terminar. Eso indica que la carga finalizó
correctamente; los archivos se verifican en las rutas `ms1/`, `ms2/` y
`ms3/` del bucket S3.

El script usa `flock` para evitar que dos ejecuciones se solapen. La variable
`IMAGE_TAG` permite seleccionar la versión publicada de las imágenes.
