FROM python:3.13-slim

# Set environtment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Add a working directory for the container 
WORKDIR /usr/src/app/

# Copyt the requirements file to the container and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copyt all the code to the container
COPY . .

EXPOSE 8000

RUN chmod +x /usr/src/app/start.sh

# Usar Gunicorn como servidor WSGI en lugar del servidor de desarrollo
CMD ["/bin/bash", "/usr/src/app/start.sh"]