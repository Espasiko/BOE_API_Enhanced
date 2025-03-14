BOE_API
=======
BOE API, is a REST API for Boletín Oficial del Estado(Official State Bulletin) of Spain. It fetches information from www.boe.es
and stores it in a PostgreSQL DB (Required for performance optimizations).

Funcionalidades Principales
=======
- Búsqueda y consulta de documentos del BOE
- Integración con Qdrant para búsqueda semántica
- Integración con Mistral para análisis de documentos
- Comparador de versiones de documentos utilizando Cohere
- Interfaz web con soporte para tema claro y oscuro

Nuevas Características
=======
- **Integración con Qdrant**: Búsqueda semántica de documentos con colección "boe_documentos"
- **Integración con Mistral**: Procesamiento avanzado de respuestas y extracción de información relevante
- **Comparador de Versiones**: Análisis detallado de diferencias entre versiones de documentos usando Cohere
- **Sistema de Relevancia**: Cálculo de relevancia combinando búsqueda exacta (60%) y semántica (40%)
- **Mejoras en la UI**: Soporte para tema claro y oscuro, mejoras visuales en todas las páginas

Requirements
=======

Tested on Ubuntu 12.04 and Windows.

- PostgreSQL 9.1
- Memcache (optional, if you're not going to use it, delete it from settings)
- Qdrant (para búsqueda semántica)
- API keys para Cohere y Mistral
- Install ```python pip install -r requirements.txt```

Configuración
=======
Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:
```
COHERE_API_KEY=tu_clave_api_cohere
MISTRAL_API_KEY=tu_clave_api_mistral
QDRANT_HOST=tu_host_qdrant
QDRANT_PORT=tu_puerto_qdrant
```

Use
=======
Sincronize DB:
```python
python manage.py syncdb
```

To execute the API:
```python
python manage.py runserver
```
Go to your browser and type ```http://localhost:8080/v1/format=json``` and you should see API's endpoints.

To fetch new laws (from BOE.es) you can execute:
```python
python manage.py getNewInfo 
```
and will fetch documents since last day stored on database or since 1960 if the database is empty.

You can pass a date to fetch laws since that date:

```python
python manage.py getNewInfo YYYY  
python manage.py getNewInfo YYYY MM
python manage.py getNewInfo YYYY MM DD
```

Despliegue en PythonAnywhere
=======
1. Clona este repositorio en tu cuenta de PythonAnywhere
2. Configura una aplicación web apuntando a la carpeta del proyecto
3. Configura las variables de entorno necesarias
4. Instala las dependencias con `pip install -r requirements.txt`
5. Configura la base de datos PostgreSQL
6. Reinicia la aplicación web
