import geopandas as gpd
import ckan.model as model
from ckan.plugins import toolkit
import json, logging,os,  mimetypes,zipfile,tempfile,sys,shutil
from datetime import datetime
import ckan.lib.helpers as h


log = logging.getLogger(__name__)


class Zip_Shp_JSONConverter:
    
    
    @staticmethod
    def zip_shp_to_geojson(file_storage, output_path=None,dataset_name=None):

        log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson ejecutado")
        """
        Convierte un shapefile dentro de un ZIP (recibido como FileStorage) a GeoJSON.
        """
       
        #log.info("[Zip_Shp_JSONConverter] convert_shp_geojson file_storage: %s", file_storage) 
        
        try:
                
            
            # Crear carpeta temporal
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, file_storage.filename)

                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson zip_path=%s",zip_path)

                # Guardar el ZIP subido en el directorio temporal
                file_storage.save(zip_path)

                # Extraer el ZIP
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # Buscar el .shp dentro del ZIP
                shp_file = None
                for root, _, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith(".shp"):
                            shp_file = os.path.join(root, f)
                            break

                if not shp_file:
                    #log.info("[Zip_Shp_JSONConverter] No se encontró ningún .shp dentro del ZIP")
                    h.flash_error("Error: No se encontró ningún .shp dentro del ZIP")
                    return toolkit.redirect_to(toolkit.h.url_for('Shp_GeoJson.shp_to_geojson'))
                
                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson shp_file=%s",shp_file)
                
                # Leer el shapefile con GeoPandas
                gdf = gpd.read_file(shp_file)

                ##log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson shp_file=%s",gdf)

                # Definir salida
                if not output_path:
                    output_path = os.path.join(tmpdir, os.path.splitext(file_storage.filename)[0] + ".geojson")

                
                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson output_path=%s",output_path)
                
                # Guardar como GeoJSON
                #gdf.to_file(output_path, driver="GeoJSON")
                geojson_str=gdf.to_json()

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(geojson_str)

                # Validar que se creó correctamente
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise Exception(f"Error: el archivo {output_path} no se creó correctamente")

                # Crear dataset si no existe
                context = {"user": toolkit.c.user}
                try:
                    package = toolkit.get_action("package_show")(context, {"id": dataset_name})
                except toolkit.ObjectNotFound:
                    package = toolkit.get_action("package_create")(context, {"name": dataset_name})

                
                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson package: %s", json.dumps(package, indent=2, ensure_ascii=False))

                # Nombre con extensión
                filename = os.path.basename(output_path)

                # Solo el nombre sin extensión
                name, ext = os.path.splitext(filename)

                # 5. Crear recurso en CKAN (meta, no archivo todavía)
                resource = toolkit.get_action("resource_create")(context, {
                    "package_id": package["id"],
                    "name": name,
                    "format": "GeoJSON",
                    "url": filename  # se sobreescribe al mover el archivo
                })


                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson resource create: %s", json.dumps(resource, indent=2, ensure_ascii=False))

                #Guardar el Recurso    
                resource_id = resource['id']
                
                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson resource_id=%s",resource_id)
            
                
                nuevo_nombre = resource_id[6:] 

                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson nuevo_nombre=%s",nuevo_nombre)
            
                        
                
            
                # 2 Calcular ruta destino CKAN
                geojson_res_id = resource_id # UUID del recurso
                storage_path = toolkit.config.get('ckan.storage_path')
                subdir = os.path.join('resources',geojson_res_id[0:3], geojson_res_id[3:6]) # Creacion Arbol donde va a qUUID del recurso
                dest_dir = os.path.join(storage_path,subdir)
                os.makedirs(dest_dir, exist_ok=True)
                

                # 3 Guardar Archivo
                nuevo_nombre = resource_id[6:] 
                dest_path = os.path.join(dest_dir, nuevo_nombre)
                
                if dataset_name is not None:
                    shutil.move(output_path, dest_path)
                    
                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson dest_path=%s",dest_path)

                # 4 Obtener size, last_modified y mimetype
                size = os.path.getsize(dest_path)
                last_modified = datetime.fromtimestamp(os.path.getmtime(dest_path))
                mimetype, encoding = mimetypes.guess_type(output_path, strict=True)
                

                # 1. Obtener el recurso completo
                #resource = toolkit.get_action('resource_show')(context, {'id': resource_id})

                # 5. Actualizar solo los campos que quieras cambiar
                resource['url_type'] = 'upload'
                resource['size'] = size
                resource['mimetype'] = mimetype
                resource['last_modified'] = last_modified.isoformat()

                
                # Mandar el recurso completo a update
                updated_resource = toolkit.get_action('resource_update')(context, resource)

                #log.info("[Zip_Shp_JSONConverter] zip_shp_to_geojson updated_resource: %s", json.dumps(updated_resource, indent=2, ensure_ascii=False))
                
                # Limpieza del temporal
                shutil.rmtree(tmpdir)
            
            
            return package  # o `output_path` si prefieres solo la ruta

        except Exception as e:
            log.info("[Zip_Shp_JSONConverter] Error: %s",e)           
            return  False
    
    @classmethod
    def listar_dataset(self):
        
        log.info("[Zip_Shp_JSONConverter] listar_dataset ejecutado")
        # El context suele incluir al usuario (puede ser sysadmin)
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user  # o el nombre de un usuario válido
        }


        data_dict = {
            'all_fields': True,   # Si quieres que traiga más datos
            'include_extras': True
        }

        packages = toolkit.get_action('package_list')(context, data_dict)

        '''for org in orgs:
            print(org['name'], "-", org.get('title'))'''

        return packages  
    
    @classmethod
    def listar_organizaciones(self):
        log.info("[Zip_Shp_JSONConverter] listar_organizaciones ejecutado")
        # El context suele incluir al usuario (puede ser sysadmin)
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user  # o el nombre de un usuario válido
        }


        data_dict = {
            'all_fields': True,   # Si quieres que traiga más datos
            'include_extras': True
        }

        orgs = toolkit.get_action('organization_list')(context, data_dict)

        '''for org in orgs:
            print(org['name'], "-", org.get('title'))'''

        return orgs  