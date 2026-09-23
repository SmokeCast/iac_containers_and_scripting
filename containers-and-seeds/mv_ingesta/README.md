# MV de ingesta

Esta carpeta contiene el Compose de despliegue y las variables de la MV de
ingesta. El Compose usa imágenes publicadas en Docker Hub; el código fuente y
los Dockerfiles están en [`data-ingestion/`](../../../data-ingestion/).

```bash
cp env.example .env
# Cambia empuiquin24 en docker-compose.yml si utilizas otro usuario de Docker Hub.
# Define los hosts privados de la MV de bases de datos en .env.
docker compose pull
docker compose run --rm fires-ingestion
docker compose run --rm cities-ingestion
docker compose run --rm weather-ingestion
```

También puedes ejecutar los tres workers con el script incluido:

```bash
./run-ingestion.sh
```

## Configurar cron paso a paso

Cron es el planificador de tareas de Linux. No mantiene los contenedores
levantados: inicia el script a la hora indicada y el script ejecuta los tres
workers uno después de otro.

### 1. Preparar la MV

Instala y activa cron en Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y cron
sudo systemctl enable --now cron
```

Comprueba que Docker funciona con el mismo usuario que ejecutará cron:

```bash
docker ps
```

Si Docker requiere `sudo`, agrega el usuario al grupo Docker y vuelve a iniciar
sesión:

```bash
sudo usermod -aG docker "$USER"
```

### 2. Preparar el Compose y las variables

Entra a la carpeta real donde se encuentra este Compose y copia el archivo de
ejemplo:

```bash
cd /opt/smokecast/mv_ingesta
cp env.example .env
nano .env
```

Completa como mínimo `S3_BUCKET`, `AWS_REGION`, los tres hosts de base de datos
y las credenciales de conexión. Si la MV usa un rol IAM como `LabRole`, deja
vacías las variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y
`AWS_SESSION_TOKEN`.

Descarga las imágenes y prueba el script manualmente:

```bash
docker compose --env-file .env pull
chmod +x run-ingestion.sh
./run-ingestion.sh
```

No avances hasta confirmar que los archivos aparecen en las rutas `ms1/`,
`ms2/` y `ms3/` del bucket S3.

### 3. Registrar la tarea periódica

Abre el crontab del usuario que tiene permiso para usar Docker:

```bash
crontab -e
```

Agrega esta línea para ejecutarla todos los días a las 02:00. Cambia la ruta
si instalaste el proyecto en otro lugar:

```cron
0 2 * * * /opt/smokecast/mv_ingesta/run-ingestion.sh >> /var/log/smokecast-ingesta.log 2>&1
```

Guarda el archivo y comprueba que quedó registrado:

```bash
crontab -l
```

La expresión `0 2 * * *` significa minuto 0, hora 2, cualquier día del mes,
cualquier mes y cualquier día de la semana. Por ejemplo, cada seis horas sería:

```cron
0 */6 * * * /opt/smokecast/mv_ingesta/run-ingestion.sh >> /var/log/smokecast-ingesta.log 2>&1
```

### 4. Revisar ejecuciones

Consulta el log generado por cron:

```bash
tail -f /var/log/smokecast-ingesta.log
```

Si no tienes permiso para escribir en `/var/log`, cambia la salida a una ruta
del usuario, por ejemplo:

```cron
0 2 * * * /opt/smokecast/mv_ingesta/run-ingestion.sh >> /home/ubuntu/smokecast-ingesta.log 2>&1
```

El script usa `flock` para impedir que dos ejecuciones se solapen. Cada job
termina después de cargar los datos; cron será quien inicie la siguiente
ejecución.

`IMAGE_TAG` permite seleccionar la versión publicada por los scripts de
`image-publishing`. Los tres servicios son procesos puntuales y no se reinician
automáticamente. Para ejecutarlos periódicamente, programa estos mismos
comandos desde cron en la MV de ingesta. El script `run-ingestion.sh` usa
`flock` para evitar ejecuciones solapadas.

Por ejemplo, para ejecutar la ingesta diariamente a las 02:00:

```cron
0 2 * * * /opt/smokecast/mv_ingesta/run-ingestion.sh >> /var/log/smokecast-ingesta.log 2>&1
```

El cron debe usar la ruta real donde clones esta carpeta. Los workers terminan
al completar la carga; cron es quien inicia una nueva ejecución periódica.
