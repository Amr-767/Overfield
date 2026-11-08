# AgroSpace Quest — Django backend (Phase 2 Step 0)
#
# GeoDjango needs native GEOS, GDAL and PROJ libraries that are not practical to
# install on a Windows host, so Django runs inside Docker (ADR-018).
# The base image pins the same Python minor version as the Phase 1 host venv.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.dev

# Geospatial runtime + development libraries:
#   libgeos-dev      -> GEOS (geometry engine used by django.contrib.gis.geos)
#   libgdal-dev      -> GDAL (geometry parsing/serialization, PROJ integration)
#   gdal-bin         -> gdalinfo/ogr2ogr utilities for diagnostics
#   libproj-dev      -> PROJ coordinate transformation runtime + data
#   proj-bin         -> proj/projinfo CLIs for CRS diagnostics
#   binutils         -> lets ctypes.util.find_library locate the shared objects
#   libpq5           -> PostgreSQL client library for psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        proj-bin \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first so application edits do not invalidate the pip layer.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . ./

EXPOSE 8000

# Local development server with autoreload; the source tree is bind-mounted in
# Compose, so edits on the host trigger a restart inside the container.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
