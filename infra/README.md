# gcp-chatbot-terraform/infra/README.md

# GCP Chatbot Infrastructure

Este documento proporciona instrucciones sobre cómo desplegar la infraestructura necesaria para el chatbot utilizando Terraform en Google Cloud Platform (GCP).

## Requisitos Previos

Antes de comenzar, asegúrate de tener instalado lo siguiente:

- [Terraform](https://www.terraform.io/downloads.html)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)

## Configuración del Proyecto

1. **Clona el repositorio**:

   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd gcp-chatbot-terraform/infra
   ```

2. **Autenticación en GCP**:

   Asegúrate de estar autenticado en tu cuenta de Google Cloud:

   ```bash
   gcloud auth login
   ```

3. **Configura el proyecto de GCP**:

   Establece el proyecto de GCP que utilizarás:

   ```bash
   gcloud config set project <NOMBRE_DEL_PROYECTO>
   ```

## Inicialización de Terraform

Ejecuta el siguiente comando para inicializar el directorio de Terraform:

```bash
terraform init
```

## Aplicar la Configuración

Para desplegar la infraestructura, ejecuta:

```bash
terraform apply
```

Revisa los cambios que se realizarán y confirma la aplicación escribiendo `yes` cuando se te solicite.

## Salidas

Después de aplicar la configuración, Terraform mostrará las salidas definidas en `outputs.tf`, que incluirán información relevante sobre los recursos creados.

## Limpieza

Para eliminar los recursos creados, puedes ejecutar:

```bash
terraform destroy
```

Confirma la eliminación escribiendo `yes` cuando se te solicite.

## Notas Adicionales

Asegúrate de revisar los archivos `variables.tf` y `outputs.tf` para personalizar la configuración según tus necesidades.