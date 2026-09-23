# Publicación de imágenes Docker

Estos scripts solo construyen y publican imágenes. No modifican ningún Compose,
no reemplazan usuarios en archivos y no ejecutan contenedores.

Antes de ejecutarlos, inicia sesión en Docker Hub:

```bash
docker login
```

Descarga el script correspondiente en la raíz del proyecto o de la MV, junto a
las carpetas `ms1-fire-catalog`, `ms2-urban-exposure`, etc. Por ejemplo:

```bash
chmod +x publish-microservices.sh
./publish-microservices.sh empuiquin24
```

Para publicar la ingesta, el script debe estar junto a la carpeta
`data-ingestion`:

```bash
chmod +x publish-ingestion.sh
./publish-ingestion.sh empuiquin24
```

El primer argumento es el usuario u organización de Docker Hub. El segundo es
opcional; si se omite, se usa el tag `latest`.

Las imágenes generadas son:

```text
<usuario>/smokecast-ms1-fire-catalog:<tag>
<usuario>/smokecast-ms2-urban-exposure:<tag>
<usuario>/smokecast-ms3-atmosphere-feed:<tag>
<usuario>/smokecast-ms4-smoke-brain:<tag>
<usuario>/smokecast-ms5-analytics-gateway:<tag>
<usuario>/smokecast-ingesta-fires:<tag>
<usuario>/smokecast-ingesta-cities:<tag>
<usuario>/smokecast-ingesta-weather:<tag>
```

En la MV de destino, la persona que despliega debe editar el usuario, nombre
de imagen y tag en el Compose correspondiente, o definir las variables que ese
Compose utilice, y después ejecutar `docker compose pull`.

El Compose de despliegue de ingesta está en
`containers-and-seeds/mv_ingesta/docker-compose.yml`; el de los microservicios
está en `containers-and-seeds/mv_microservicios/docker-compose.yml`.

Compose no busca cualquier tag local: el nombre y tag deben coincidir
exactamente. Si publicas `v1.0.0`, configura ese mismo tag en el Compose. Si
dejas `latest`, las imágenes locales `...:latest` serán utilizadas directamente
sin hacer `pull`.

Para limpiar imágenes locales antiguas sin tocar las imágenes `latest` que usa
el despliegue:

```bash
chmod +x cleanup-local-images.sh
./cleanup-local-images.sh       # solo muestra candidatos
./cleanup-local-images.sh --apply
```
