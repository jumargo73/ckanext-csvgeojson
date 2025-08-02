from ckan.plugins import SingletonPlugin, implements, IBlueprint
from flask import Blueprint, request, jsonify
from ckan.plugins.toolkit import get_action
from shapely.geometry import Point, mapping
import json, tempfile, logging

log = logging.getLogger(__name__)

class CSVtoGeoJSONDatapusherPlugin(SingletonPlugin):
    implements(IBlueprint)
    log.info("[CSVtoGeoJSONPlugin] CSVtoGeoJSONDatapusher Cargado con Exito")

    def get_blueprint(self):
        """
        Crea un Blueprint que escucha el mismo endpoint /api/3/action/datapusher_hook
        pero en paralelo, sin reemplazar la funcionalidad oficial de CKAN/DataPusher.
        """
        log.info("[CSVtoGeoJSONPlugin] get_blueprint ejecutado")
        bp = Blueprint('csvgeojson_hook', __name__)

        @bp.route('/api/3/action/datapusher_hook_GeoJson', methods=['POST'])
        def datapusher_hook_listener():
            """
            Se ejecuta cuando DataPusher termina de procesar un CSV.
            Procesa el CSV en DataStore y crea un GeoJSON adicional.
            """
            try:
                log.info("[CSVtoGeoJSONPlugin] datapusher_hook_listener")
                payload = request.get_json(force=True) or {}
                resource_id = payload.get('resource_id')

                if not resource_id:
                    log.error("[CSVtoGeoJSONPlugin] Sin resource_id en datapusher_hook")
                    return jsonify({"success": False})

                log.info(f"[CSVtoGeoJSONPlugin] Hook recibido para recurso {resource_id}")

                # Lógica de conversión
                self.convertir_csv_geojson(resource_id)

            except Exception as e:
                log.error(f"[CSVtoGeoJSONPlugin] Error procesando hook: {e}")

            # Siempre devolver success para no interrumpir CKAN
            return jsonify({"success": True})

        return bp

    # ----------------- Lógica principal -----------------

    def convertir_csv_geojson(self, resource_id):
        """
        Convierte el recurso CSV en GeoJSON usando los datos de DataStore
        y crea un recurso nuevo en el mismo dataset.
        """
        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson ejecutado")
        context = {'ignore_auth': True}

        # 1. Obtener metadatos del recurso
        resource = get_action('resource_show')(context, {'id': resource_id})
        if resource.get('format', '').lower() != 'csv':
            log.info(f"[CSVtoGeoJSONPlugin] Recurso {resource_id} no es CSV, se ignora.")
            return

        # 2. Verificar que DataPusher haya completado
        if resource.get('datapusher_status') != 'complete':
            log.info(f"[CSVtoGeoJSONPlugin] Recurso {resource_id} aún no está completo.")
            return

        # 3. Obtener datos desde DataStore
        data = get_action('datastore_search')(context, {'resource_id': resource_id})
        records = data.get('records', [])
        if not records:
            log.error(f"[CSVtoGeoJSONPlugin] Sin datos en DataStore para {resource_id}")
            return

        # 4. Detectar columnas lat/lon
        columnas = list(records[0].keys())
        lat_col, lon_col = self.detectar_columnas_coord(columnas)

        if not lat_col or not lon_col:
            log.warning(f"[CSVtoGeoJSONPlugin] No se detectaron columnas lat/lon en {resource_id}")
            return

        # 5. Convertir a GeoJSON
        geojson = self.convertir_a_geojson(records, lat_col, lon_col)

        # 6. Crear recurso GeoJSON en el mismo dataset
        self.crear_recurso_geojson(resource['package_id'], resource['name'], geojson)

    # ----------------- Utilidades -----------------

    def detectar_columnas_coord(self, columnas):
        log.info("[CSVtoGeoJSONPlugin] detectar_columnas_coord ejecutado")
        lat_variants = ['lat', 'latitude', 'latitud']
        lon_variants = ['lon', 'lng', 'longitud', 'longitude']
        lat_col = next((c for c in columnas if c.lower() in lat_variants), None)
        lon_col = next((c for c in columnas if c.lower() in lon_variants), None)
        return lat_col, lon_col

    def convertir_a_geojson(self, records, lat_col, lon_col):
        log.info("[CSVtoGeoJSONPlugin] convertir_a_geojson ejecutado")
        features = []
        for row in records:
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
                features.append({
                    "type": "Feature",
                    "geometry": mapping(Point(lon, lat)),
                    "properties": row
                })
            except (ValueError, TypeError):
                continue

        return json.dumps({
            "type": "FeatureCollection",
            "features": features
        }, ensure_ascii=False)

    def crear_recurso_geojson(self, package_id, nombre_origen, geojson):
        log.info("[CSVtoGeoJSONPlugin] crear_recurso_geojson ejecutado")
        context = {'ignore_auth': True}
        create_resource = get_action('resource_create')

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.geojson')
        tmp_file.write(geojson.encode('utf-8'))
        tmp_file.close()

        with open(tmp_file.name, 'rb') as f:
            create_resource(context, {
                'package_id': package_id,
                'name': f"{nombre_origen} (GeoJSON)",
                'format': 'GeoJSON',
                'upload': f,
                'description': 'Recurso generado automáticamente desde CSV'
            })
