1. Estructura de carpetas

	ckanext-csvgeojson/
	│
	├── docs/
	│   └── flowchart.png      # Diagrama PNG
	│
	├── ckanext/
	│   └── csvgeojson/
	│       ├── plugin.py
	│       └── services/
	│           └── geojson_converter.py
	│
	└── README.md

2. Contenido de README.md

# CKANEXT-CSVGEOJSON

Extensión para **CKAN** que convierte recursos **CSV** en **GeoJSON** automáticamente y mediante un endpoint manual, almacenando el resultado en el storage nativo de CKAN.

---

## Características

- Conversión automática en `after_resource_update`.
- Conversión manual vía API (`/api/3/action/convert_csv_to_geojson`).
- Detección de columnas de coordenadas (`Lat`, `Lon`, `Latitud`, `Longitud`, etc.).
- Creación/actualización de recurso GeoJSON vinculado al dataset original.
- Copia manual del `.geojson` al storage de CKAN (`/var/lib/ckan/default/resources`).
- Compatible con vistas `ckanext-geoview`.

---

## Diagrama de flujo

![Flujo CSV a GeoJSON](docs/flowchart.png)

---

## Endpoint manual

**URL:**
POST /api/3/action/convert_csv_to_geojson

**Headers:**
Content-Type: application/json
Authorization: <API_KEY>

css

**Body:**
json
{
  "resource_id": "6ef7d6bc-e5d5-46ab-97d4-5321c93dd49f"
}
Respuesta:

json

{
  "success": true,
  "message": "GeoJSON generado/actualizado para recurso 6ef7d6bc-e5d5-46ab-97d4-5321c93dd49f"
}

Instalación


Activar el Entorno virtual de ckan

. /usr/lib/ckan/default/bin/activate


Clonar el repositorio en el entorno CKAN:


cd /home/ckan/ckan/lib/default/src
git clone https://github.com/jumargo73/ckanext-csvgeojson.git

Instalar dependencias:

pip install -e ckanext-csvgeojson

Activar el plugin en ckan.ini:

ini
ckan.plugins = ... csv_to_geojson_api,csv_to_geojson_dataset_resource

Reiniciar CKAN:

sudo service supervisor restart
sudo service nginx restart

Ejemplo curl

curl -X POST "http://www.datosabiertos.valledelcauca.gov.co/api/3/action/convert_csv_to_geojson" \
     -H "Authorization: TU_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"resource_id": "6ef7d6bc-e5d5-46ab-97d4-5321c93dd49f"}'

Troubleshooting
GeoJSONConverter.detectar_columnas_coord() missing 1 required positional argument
→ Usar GeoJSONConverter.detectar_columnas_coord(columnas) correctamente.

LazyJSONObject en records
→ Convertir con records = list(data.get('records', [])).

FileNotFoundError al descargar
→ Asegurar copia manual en /var/lib/ckan/default/resources/<3>/<3>/<resto>.

Error 400 en endpoint
→ Revisar formato JSON y API Key en la petición.
