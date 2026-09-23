FROM python:3.13-slim

ARG VERSION=dev
LABEL org.opencontainers.image.title="SmokeCast database seeder" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.description="Carga inicial masiva de datos de SmokeCast"

WORKDIR /workspace
COPY iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/requirements.txt /workspace/iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/requirements.txt
RUN pip install --no-cache-dir -r iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/requirements.txt

COPY iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/ /workspace/iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds/
COPY frontend-web/src/south-america.json /workspace/frontend-web/src/south-america.json

WORKDIR /workspace/iac_containers_and_scripting/containers-and-seeds/mv_databases/seeds
ENTRYPOINT ["python", "seed_data.py"]
CMD ["--database", "all", "--fires", "100000", "--weather", "100000", "--sites", "25000"]
