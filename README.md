# cloud-formation-iac
IaC con las plantillas para deployar todas las máquinas virtuales y recursos necesarios en CloudFormation

La carpeta [`image-publishing`](./image-publishing) contiene los scripts
independientes para construir y publicar las imágenes Docker de los
microservicios y de la ingesta. No modifican los archivos Compose.

## Plantillas CloudFormation

Las plantillas se despliegan en este orden:

1. `iac_crear_smokecast_mv_prod_alb.yml`: dos EC2, ALB interno, listeners y
   target groups. Conserva los outputs `AlbSecurityGroupId` y
   `Listener8081Arn`–`Listener8085Arn`.
2. `iac_crear_smokecast_mv_databases.yml`: MV de bases. Usa la misma `VpcId` y
   una `SubnetId`; recibe los Security Groups de producción e ingesta.
3. `iac_crear_smokecast_ingesta.yml`: MV de ingesta, S3 y catálogo Glue. Usa la
   misma `VpcId` y una `SubnetId` de la MV de ingesta.
4. `iac_crear_smokecast_api_gateway.yml`: API Gateway HTTP y VPC Link. Recibe
   la VPC, dos subredes, el Security Group del ALB y los cinco ARN de listeners.

La plantilla de API Gateway no crea una VPC ni un ALB. El ALB queda interno y
solo recibe tráfico desde el Security Group del VPC Link. Antes de desplegarla,
retira cualquier regla `0.0.0.0/0` del Security Group del ALB para los puertos
8081–8085.
