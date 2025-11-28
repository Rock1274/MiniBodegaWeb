# Imagen base completa de Python 3.11
FROM python:3.11

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias del sistema necesarias para pyodbc
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       unixodbc-dev \
       curl \
       gnupg \
       lsb-release \
       apt-transport-https \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Exponer el puerto (ajusta si tu app Flask u otra usa otro puerto)
EXPOSE 5000

# Comando por defecto
CMD ["python", "app.py"]
