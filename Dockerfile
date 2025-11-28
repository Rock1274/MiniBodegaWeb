FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema y ODBC Driver
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl gnupg lsb-release apt-transport-https ca-certificates build-essential unixodbc-dev software-properties-common \
 && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
 && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Carpeta de trabajo
WORKDIR /app
COPY . /app

# Instalar librerías Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Puerto que Render inyecta
ENV PORT=10000

CMD ["sh", "-c", "gunicorn app:app -b 0.0.0.0:${PORT}"]
