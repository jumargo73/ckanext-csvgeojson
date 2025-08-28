import os, json, tempfile, shutil, mimetypes
from datetime import datetime
from shapely.geometry import Point, mapping
from ckan.plugins.toolkit import get_action
import logging

log = logging.getLogger(__name__)

storage_path = '/var/lib/ckan/default/resources'

class GeoJSONConverter:
    
    @staticmethod
    def detectar_columnas_coord(columnas):
        
        log.info("[CSVtoGeoJSONPlugin] convertir_a_geojson ejecutado")
        
        lat_variants = ['lat', 'latitude', 'latitud']
        lon_variants = ['lon', 'lng', 'longitud', 'longitude']
        lat_col = next((c for c in columnas if c.lower() in lat_variants), None)
        lon_col = next((c for c in columnas if c.lower() in lon_variants), None)
        return lat_col, lon_col

    @staticmethod
    def convertir_a_geojson(records, lat_col, lon_col):
        
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
    
    @classmethod
    def convertir_csv_geojson(cls, resource_id, geojson_id=None):
        """
        Convierte un recurso CSV del DataStore en GeoJSON.
        Si geojson_id está presente, actualiza el recurso existente;
        si no, crea uno nuevo.
        """
        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson ejecutado para recurso CSV %s", resource_id)

        context = {'ignore_auth': True}

        # 1. Obtener información del recurso CSV
        resource = get_action('resource_show')(context, {'id': resource_id})
        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson Recurso Encontrado: %s", json.dumps(resource, indent=2, ensure_ascii=False))
        package_id = resource['package_id']
        nombre_origen = resource['name']

        # 2. Obtener datos del DataStore
        data = get_action('datastore_search')(context, {'resource_id': resource_id})
        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson data Encontrado: %s", data)
        records = data.get('records', [])
        if not records:
            log.error("[CSVtoGeoJSONPlugin] convertir_csv_geojson Sin datos en DataStore para %s", resource_id)
            return

        # 3. Detectar columnas lat/lon
        columnas = list(records[0].keys())
        lat_col, lon_col = cls.detectar_columnas_coord(columnas)
        if not lat_col or not lon_col:
            log.warning("[GeoJSONConverter] No se detectaron columnas lat/lon en %s", resource_id)
            return
            
        # 4. Convertir a GeoJSON
        geojson = cls.convertir_a_geojson(records, lat_col, lon_col)

        # 5. Crear archivo temporal
        tmp_dir = tempfile.mkdtemp()
        base_name = os.path.splitext(nombre_origen)[0]          # ZonaWifi.csv -> ZonaWifi
        safe_name = base_name.replace(" ", "_") + ".geojson"    # ZonaWifi.geojson
        tmp_path = os.path.join(tmp_dir, safe_name)
        
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(geojson)
            
        size = os.path.getsize(tmp_path)
        mime = mimetypes.guess_type(tmp_path)[0] or 'application/geo+json'    

        # 6. Crear o actualizar recurso GeoJSON
        if geojson_id:
            # Actualizar recurso existente
            log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson Actualizando recurso GeoJSON existente ID=%s", geojson_id)
            update_data = {
                'id': geojson_id,
                'format': 'GeoJSON',
                'url_type': 'upload',
                'size': size,
                'mimetype': mime,
                'last_modified': datetime.utcnow().isoformat(),
                'url': safe_name
            }
            response =  get_action('resource_update')(context, update_data)
            
        else:
            # Crear recurso nuevo
            log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson Creando nuevo recurso GeoJSON para paquete %s", package_id)
            create_data = {
                'package_id': package_id,
                'name': f"{base_name} (GeoJSON)",
                'format': 'GeoJSON',
                'description': 'Recurso generado automáticamente desde CSV',
                'url_type': 'upload',
                'size': size,
                'mimetype': mime,
                'last_modified': datetime.utcnow().isoformat(),
            }
            with open(tmp_path, 'rb') as f:
                create_data['upload'] = f
                response =  get_action('resource_create')(context, create_data)
                log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson crear_recurso_geojson Recurso creado: %s", json.dumps(response, indent=2, ensure_ascii=False))
                
        
        # Parchar el campo `url` para que tenga el nombre correcto del archivo
        get_action('resource_patch')(context, {
            'id': response['id'],
            'url': safe_name
        })

        # 7. Copiar archivo manualmente al storage_path
        
        geojson_res_id = response.get('id')

        # CKAN divide el UUID en carpetas de 3 caracteres
        subdir = os.path.join(geojson_res_id[0:3], geojson_res_id[3:6])
        dest_dir = os.path.join(storage_path, subdir)
        os.makedirs(dest_dir, exist_ok=True)

        shutil.copy(tmp_path, os.path.join(dest_dir, geojson_res_id[6:]))

        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson GeoJSON copiado manualmente a %s", os.path.join(dest_dir, geojson_res_id[6:]))
            
        # 8. Limpiar archivo temporal
        shutil.rmtree(tmp_dir)
        log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojsonConversión a GeoJSON completada para %s", resource_id)

    # Métodos auxiliares
    
   
    