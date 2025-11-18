from ckan.plugins import SingletonPlugin, implements, IBlueprint
from flask import Blueprint, request, jsonify
from ckan.plugins.toolkit import get_action,ObjectNotFound
from shapely.geometry import Point, mapping
import json, tempfile, logging
from ckan.common import config
from ckan.model import Session,Contador,Resource
import json
from flask import Response

log = logging.getLogger(__name__)


class DataJson(SingletonPlugin):
    implements(IBlueprint)
    log.info("[DataJson] DataJson Cargado con Exito")

    def get_blueprint(self):
        bp = Blueprint('data_json', __name__)

        log.info("[DataJson] get_blueprint_geojson ejecutado")

        @bp.route('/power_BI/data.json', methods=['GET'])
        def powerBI():

            """
            EndPoint para Tableros
            """

            log.info("[DataJson] get_blueprint powerBI ejecutado")
           
            try:
                context = {'ignore_auth': True}

                packages=get_action('package_list')({}, {})

                url_site=config.get('ckan.site_url')
                
                data={
                    "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
                    "@type": "dcat:Catalog", 
                    "conformsTo": "https://project-open-data.cio.gov/v1.1/schema", 
                    "describedBy": "https://project-open-data.cio.gov/v1.1/schema/catalog.json",
                    'dataset':[],
                }

                for package in packages:

                    log.info(f"[DataJson] Package_name {package}")
                    
                    try:
                        package_response = get_action('package_show')(context, {'id': package})
                    except ObjectNotFound:
                        return {"ok": False, "reason": "Recurso no existe en CKAN"}    

                    log.info(f"[DataJson] package_response {package_response}")

                    log.info(f"[DataJson] type {package_response.get('type')}")

                    if package_response.get('type', '').lower() != 'harvest':
                        
                        #faltantes = self.validar_campos(package_response)

                        #log.info(f"[DataJson] faltantes {faltantes}")

                        resources=package_response['resources'] 
                        organization=package_response['organization'] 
                        groups=package_response['groups'] 

                        package_id=package_response['id']
                        
                        
                        
                        
                        grupos= package_response.get('groups') if package_response else []
                        #log.info(f"[DataJson] organization {grupos}")
                        title=organization.get('title') if organization else ''
                        #log.info(f"[DataJson] organization {title}")
                        type_organization=organization.get('type') if organization else None
                        #log.info(f"[DataJson] type_organization {type_organization}")
                        nombre=package_response.get('title') if organization else None
                        #log.info(f"[DataJson] title {nombre}")
                        notes=package_response.get('notes') if organization else None
                        #log.info(f"[DataJson] notes {notes}")
                        metadata_created=package_response.get('metadata_created') if organization else None
                        #log.info(f"[DataJson] metadata_created {metadata_created}")
                        metadata_modified=package_response.get('metadata_modified') if organization else None
                        #log.info(f"[DataJson] metadata_modified {metadata_modified}")
                        ciudad=package_response.get('ciudad') if organization else None
                        #log.info(f"[DataJson] ciudad {ciudad}")
                        departamento=package_response.get('departamento') if organization else None
                        #log.info(f"[DataJson] departamento {departamento}")
                        frecuencia_actualizacion=package_response.get('frecuencia_actualizacion') if organization else None
                        #log.info(f"[DataJson] frecuencia_actualizacion {frecuencia_actualizacion}")
                        type_dataset=package_response.get('type') if package_response else None
                        #log.info(f"[DataJson] type_dataset {type_dataset}")
                        tags=package_response.get('tags') if package_response else []
                        #log.info(f"[DataJson] tags {tags}")
                        license_id=package_response.get('license_id') if package_response else None
                        #log.info(f"[DataJson] license_id {license_id}")

                        data_dataset={
                            "@type":"dcat:Dataset",
                            "identifier":package_id, 
                            "landingPage":"{}".format(url_site+'/'+type_dataset+'/'+package_id),   
                            "Nombre":nombre,
                            "Descripcion":notes,
                            "Dependencia":title,
                            "issued":metadata_created,
                            "modified":metadata_modified,
                            "ciudad":ciudad,
                            "departamento":departamento,
                            "Frecuencia_actualizacion":frecuencia_actualizacion,
                            "distribution":[],
                            "keyword":tags,
                            "publisher":{
                                "@type": "{}".format("org:"+title),
                                "name": "Gobernacion Valle del Cauca"
                            },
                            "contactPoint":{
                                 "@type": "vcard:Contact", 
                                "hasEmail": "mailto:wgonzalez@sdp.gov.co", 
                                "fn": type_organization
                            },
                            "accessLevel":"Public",
                            'license':license_id,
                            "theme":[],
                           
                        }
                        
                        data_dataset['theme'].append(grupos)

                        
                        for resource in  resources:

                            #log.info(f"[DataJson] Resource {resource}")
                            resource_id=resource['id']
                            counter=self.get_or_create_counter(resource_id,package_id)
                            #log.info(f"[DataJson] resource_id {resource_id}")

                            if not resource.get("datastore_active", False):

                                try:
                                    #log.warning("[DataJson] buscado extras con ID: %s", resource_id)
                                    resource_model = Session.query(Resource).filter(
                                        Resource.format.ilike('PDF'),
                                        Resource.id == resource_id
                                    ).first()

                                    if not resource_model:
                                        log.warning("[DataJson] No se encontró recurso con ID: %s", resource_id)
                                        continue

                                    extras = {}

                                    if resource_model.extras:
                                        if isinstance(resource_model.extras, str):
                                            try:
                                                extras = json.loads(resource_model.extras)
                                            except Exception:
                                                log.error("[DataJson] Error al convertir extras JSON. Se usa {}.")
                                                extras = {}
                                        elif isinstance(resource_model.extras, dict):
                                            extras = resource_model.extras

                                    #log.info("[DataJson] Extras cargados: %s", extras)
                                
                                    if extras.get('type')=="sello_excelencia":
                                        data_resource={
                                            "@type": "dcat:Distribution",
                                            "Url":url,  
                                            'categoria': extras.get('type'),
                                            'fecha_obtencion': extras.get('fecha_obtencion'),
                                            'fecha_vencimiento': extras.get('fecha_vencimiento'),
                                            'dependiencia': extras.get('owner_org'),
                                            'nivel': extras.get('nivel'),
                                            "filas":0,
                                            "columnas":0,
                                            "vistas":0,
                                            'descargas':0,
                                        }
                                    
                                except Exception as e:
                                    log.error("[DataJson] Error procesando recurso: %s", e)
                                
                                data_dataset['distribution'].append(data_resource)
                                continue
                            
                            try:
                                resource_response = get_action('datastore_search')(context, {'id': resource_id})
                            except Exception as e:
                                log.error("[DataJson] Error al convertir extras JSON. Se usa {}.")
                                continue 

                             

                            columnas = resource_response.get("fields", [])
                            filas = resource_response.get("total", 0)      

                            
                            #log.info(f"[DataJson] resource_response {resource_response}")
                            #print(f"getPaquetesjsonBI Recibido desde Funcion datastore_search {columnas} {filas}")

                            
                            #log.info(f"[DataJson] dataset_id {package_id}")
                            #log.info(f"[DataJson] resource_id {resource_id}")
                            url=resource.get('url') if resource else None; 
                            #log.info(f"[DataJson] url {resource.get('url') if resource else None }")

                            data_resource= {
                                "@type": "dcat:Distribution",
                                "Url":url,                        
                                "filas":filas,
                                "columnas":len(columnas),
                                "vistas":counter.get('contVistas') or 0,
                                'descargas':counter.get('contDownload') or 0,
                            }

                            #log.info(f"[DataJson] data_resource {data_resource}") 

                            data_dataset['distribution'].append(data_resource)
                        data['dataset'].append(data_dataset)     
            
                #print(f"/dataBI/data.json {data}")  

                return Response(json.dumps(data), mimetype="application/json")  
                #return jsonify(data)
            

            except Exception as e:
                log.error(f"[DataJson] Error procesando hook: {e}")

            # Siempre devolver success para no interrumpir CKAN
        return bp 
    
    def get_or_create_counter(self, resource_id, package_id):
        
        counter = Session.query(Contador).filter_by(
            sourceId=resource_id,
            packageId=package_id
        ).first()

        
        # Si ya existe → retornarlo
        if counter:
            return {
                "contVistas": counter.contVistas,
                "contDownload": counter.contDownload,
            }

        if not counter:
            # Caso recurso JSON/no registrado/no datastore: solo devolver valores sin insertar
            return {
                "contVistas": 0,
                "contDownload": 0,
            }
        
        
            
    def incrementar_visita(resource_id, package_id):
        counter = self.get_or_create_counter(resource_id, package_id)
        counter.contVistas += 1
        Session.commit()

class CSVtoGeoJSONDatapusherPlugin(SingletonPlugin):
    implements(IBlueprint)
    #log.info("[CSVtoGeoJSONPlugin] CSVtoGeoJSONDatapusher Cargado con Exito")

    def get_blueprint(self):
        """
        Crea un Blueprint que escucha el mismo endpoint /api/3/action/datapusher_hook
        pero en paralelo, sin reemplazar la funcionalidad oficial de CKAN/DataPusher.
        """
        #log.info("[CSVtoGeoJSONPlugin] get_blueprint ejecutado")
        bp = Blueprint('csvgeojson_hook', __name__)

        @bp.route('/api/3/action/datapusher_hook_GeoJson', methods=['POST'])
        def datapusher_hook_listener():
            """
            Se ejecuta cuando DataPusher termina de procesar un CSV.
            Procesa el CSV en DataStore y crea un GeoJSON adicional.
            """
            try:
                #log.info("[CSVtoGeoJSONPlugin] datapusher_hook_listener")
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
        #log.info("[CSVtoGeoJSONPlugin] convertir_csv_geojson ejecutado")
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
        #log.info("[CSVtoGeoJSONPlugin] detectar_columnas_coord ejecutado")
        lat_variants = ['lat', 'latitude', 'latitud']
        lon_variants = ['lon', 'lng', 'longitud', 'longitude']
        lat_col = next((c for c in columnas if c.lower() in lat_variants), None)
        lon_col = next((c for c in columnas if c.lower() in lon_variants), None)
        return lat_col, lon_col

    def convertir_a_geojson(self, records, lat_col, lon_col):
        #log.info("[CSVtoGeoJSONPlugin] convertir_a_geojson ejecutado")
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
        #log.info("[CSVtoGeoJSONPlugin] crear_recurso_geojson ejecutado")
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
