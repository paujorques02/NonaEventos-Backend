# gcp-chatbot-terraform

Este proyecto implementa un chatbot que interactúa con Google Calendar y gestiona conversaciones utilizando Firestore. El chatbot está diseñado para acceder a información sobre servicios y precios, y utiliza el modelo Gemini para el procesamiento del lenguaje natural.

## Estructura del Proyecto

El proyecto se organiza en dos directorios principales:

- **infra**: Contiene la configuración de Terraform para desplegar los recursos necesarios en Google Cloud Platform.
  - `main.tf`: Configuración principal de Terraform.
  - `variables.tf`: Definición de variables para la configuración de Terraform.
  - `outputs.tf`: Especificación de salidas de la configuración de Terraform.
  - `README.md`: Documentación sobre cómo desplegar la infraestructura.

- **src**: Contiene el código fuente del chatbot.
  - `main.py`: Punto de entrada de la aplicación del chatbot.
  - `calendar/google_calendar.py`: Funciones para interactuar con la API de Google Calendar.
  - `firestore/conversation_store.py`: Manejo de la conexión y operaciones con Firestore.
  - `gemini/llm_client.py`: Lógica para interactuar con el modelo Gemini.
  - `embeddings/embeddings_manager.py`: Gestión de embeddings para documentos.
  - `services/services_info.py`: Acceso a información de servicios y precios.

## Requisitos

Asegúrate de tener instaladas las siguientes dependencias:

- Python 3.x
- Bibliotecas para interactuar con Google Cloud, Firestore y el modelo Gemini.

Puedes instalar las dependencias ejecutando:

```
pip install -r requirements.txt
```

## Despliegue de la Infraestructura

Para desplegar la infraestructura en Google Cloud Platform, sigue estos pasos:

1. Navega al directorio `infra`.
2. Inicializa Terraform:

   ```
   terraform init
   ```

3. Aplica la configuración:

   ```
   terraform apply
   ```

Esto creará los recursos necesarios en tu cuenta de Google Cloud.

## Ejecución del Chatbot

Para ejecutar el chatbot, asegúrate de que la infraestructura esté desplegada y luego ejecuta:

```
python src/main.py
```

El chatbot estará disponible para recibir solicitudes y responder a consultas sobre el calendario y servicios.