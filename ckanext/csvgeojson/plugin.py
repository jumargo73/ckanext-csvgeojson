from ckan.plugins import SingletonPlugin,implements,IBlueprint
from ckan.plugins.toolkit import get_action,check_access, ValidationError,c
from flask import Blueprint, request, jsonify
import logging
import ckan.model as model

from ckanext.csvgeojson.services.geojson_converter import GeoJSONConverter  

log = logging.getLogger(__name__)

class CSVtoGeoJSONApiPlugin(SingletonPlugin):
    
    implements(IBlueprint)
    log.info("[CSVtoGeoJSONPlugin] CSVtoGeoJSONApi Cargado con Exito")
    def get_blueprint(self):
        """
        Crea un Blueprint con endpoint manual para convertir CSV a GeoJSON.
        """
        log.info("[CSVtoGeoJSONPlugin] get_blueprint ejecutado")

        bp = Blueprint('csvgeojson_manual', __name__)

        @bp.route('/api/3/action/convert_csv_to_geojson', methods=['POST'])
        def convert_csv_to_geojson_endpoint():
            """
            Endpoint manual: recibe resource_id y genera/actualiza GeoJSON.
            """
            try:
                payload = request.get_json(force=True) or {}
                log.info(f"[CSVtoGeoJSONPlugin] Payload recibido en endpoint manual: {payload}")

                resource_id = payload.get('resource_id')
                if not resource_id:
                    raise ValidationError({'resource_id': ['Este campo es obligatorio']})
                    
                    
                # Crear context manual
                context = {
                    'model': model,
                    'session': model.Session,
                    'user': c.user or c.author,
                    'ignore_auth': False
                }    
                
                #buscar Paquete asociado
                resource = get_action('resource_show')(context, {'id': resource_id})
                
                # Obtener dataset completo
                package = get_action('package_show')(context, {'id': resource['package_id']})
               
                
                log.info(f"[CSVtoGeoJSONPlugin] package_id encontrado con {resource['id']} : {package['id']}")    

                # Buscar recurso GeoJSON ya existente en el paquete
                geojson_resource = next(
                    (r for r in package['resources'] if r.get('format', '').lower() == 'geojson'),
                    None
                )

                if geojson_resource:
                    log.info("[CSVtoGeoJSONPlugin] GeoJSON ya existe, será actualizado (ID: %s)", geojson_resource['id'])
                    GeoJSONConverter.convertir_csv_geojson(resource['id'], geojson_resource['id'])  # Pasar ID para update
                else:
                    log.info("[CSVtoGeoJSONPlugin] No hay GeoJSON, creando nuevo")
                    GeoJSONConverter.self.convertir_csv_geojson(resource['id'])  

                return jsonify({"success": True, "message": f"GeoJSON generado para recurso {resource_id}"})

            except ValidationError as ve:
                log.error(f"[CSVtoGeoJSONPlugin] Error de validación: {ve}")
                return jsonify({"success": False, "error": str(ve)}), 400

            except Exception as e:
                log.error(f"[CSVtoGeoJSONPlugin] Error en conversión manual: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

            # CKAN requiere lista de blueprints
        return [bp]

    
    