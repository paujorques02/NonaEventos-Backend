# Usa una imagen base de Python oficial y ligera
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias primero para aprovechar el caché de Docker
COPY requirements.txt requirements.txt

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu aplicación al contenedor
COPY . .

# Expone el puerto en el que se ejecutará la aplicación
EXPOSE 8000

# El comando para iniciar la aplicación cuando el contenedor arranque
# Le dice a uvicorn que use el puerto definido en la variable de entorno PORT, o 8000 si no existe.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}