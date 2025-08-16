from ckan.plugins import SingletonPlugin, IDatasetForm, implements, IPackageController, IResourceController
from ckan.plugins import toolkit
from ckan.plugins.interfaces import IResourceView, IConfigurer, IBlueprint
from flask import Blueprint,request
import json, logging,os,  mimetypes
from datetime import datetime
import ckan.logic
import ckan.model as model
from model import Session, Resource,Package,PackageExtra
import fitz  
from ckan.types import Context 
from ckan.common import config
from typing import Any
import pprint, re                    
from ckanext.csvgeojson.services.geojson_converter import GeoJSONConverter
import ckan.lib.helpers as h
from ckan.common import request
from ckan.lib.helpers import flash_error, redirect_to
from sqlalchemy.orm import joinedload

TRUTHY = {'true', 'on', '1', 'si', 'sí'}

log = logging.getLogger(__name__)

class CSVtoGeoJSONDatasetResourcePlugin(SingletonPlugin):
    implements(IResourceController)
    implements(IPackageController)
   
    
    log.info("[CSVtoGeoJSONPlugin] CSVtoGeoJSONDatasetResourcePlugin Cargado con Exito")
    
    
    # --- resource_create ---        
    def before_resource_create(self,context: Context, resource: dict[str, Any]):
        pass
        
    def after_resource_create(self,context: Context, resource: dict[str, Any]):
        pass
        
    # --- dataset_create ---     
    def after_dataset_create(self,context: Context,  pkg_dict: dict[str, Any]):
        
        return pkg_dict
    
    # --- resource_update ---    

    def before_resource_update(self,context: Context, current: dict[str, Any], resource: dict[str, Any]):
        pass

    def after_resource_update(self, context, resource):

        
        log.info("[CSVtoGeoJSONPlugin] after_resource_update ejecutado")
        
        # Procesar solo CSV
        if resource.get('format', '').lower() == 'csv':

            # Obtener dataset completo
            package = get_action('package_show')(context, {'id': resource['package_id']})
            
            
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
                GeoJSONConverter.convertir_csv_geojson(resource['id'])

    
    # --- dataset_update ---
    
    def after_dataset_update(self,context: Context, pkg_dict: dict[str, Any]):

        log.info("[CSVtoGeoJSONPlugin] after_dataset_update ejecutado")

        if context.get('skip_sello_excelencia'):
            return    

        
        # Leer el valor del checkbox desde el formulario
        val = toolkit.request.form.get('sello_excelencia') or pkg_dict.get('sello_excelencia')

        
        # Determinar si está marcado
        is_checked = bool(val and str(val).strip().lower() in TRUTHY)

        log.info("[CSVtoGeoJSONPlugin] after_dataset_update tiene sello , %s",is_checked) 

        # Traer el dataset actual
        pkg_id = pkg_dict.get('id') or pkg_dict.get('name')
        if not pkg_id:
            return

        pkg = toolkit.get_action('package_show')({'user': context.get('user')}, {'id': pkg_id})
        extras = pkg.get('extras', [])

        # Quitar valor previo si existe
        extras = [e for e in extras if e.get('key') != 'sello_excelencia']

        # Guardar cambios
        if is_checked:
            extras.append({'key': 'sello_excelencia', 'value': 'true'})

        # ⚠️ Pasar bandera para que el evento no se dispare otra vez
        new_context = dict(context, skip_sello_excelencia=True)
        toolkit.get_action('package_patch')(new_context, {'id': pkg_id, 'extras': extras})

        log.info("[CSVtoGeoJSONPlugin] after_dataset_update Dataset Marcado con Exito")          
        

    # --- resource_delete ---
        
    def before_resource_delete(self,context: Context, resource: dict[str, Any], resources: list[dict[str, Any]]):
        pass

    def after_resource_delete(self,context: Context, resources: list[dict[str, Any]]):
        pass

    # --- dataset_delete ---
    def after_dataset_delete(self,context: Context, pkg_dict: dict[str, Any]):
        pass
    
    # --- resource_show ---
    
    def before_resource_show(self,resource_dict: dict[str, Any]):
        return resource_dict

    def before_dataset_show(self,context: Context, pkg_dict: dict[str, Any]):
        return pkg_dict
    
    
    # --- dataset_show ---   
    def after_dataset_show(self,context: Context, pkg_dict: dict[str, Any]):

        log.info("[CSVtoGeoJSONPlugin] after_dataset_show ejecutado")
        #log.info("[SelloExcelenciaView] fter_dataset_show pkg_dict devuelto: %s", json.dumps(pkg_dict, indent=2, ensure_ascii=False))    
        return pkg_dict
        
    def before_dataset_view(self,pkg_dict: dict[str, Any]):
        return pkg_dict  
        
    # --- dataset_search ---    
    def before_dataset_search(self,search_params: dict[str, Any]):
        return search_params 

    def after_dataset_search(self,search_results: dict[str, Any], search_params: dict[str, Any]):
        return search_results
    
    # --- dataset_index ---   
    
    def before_dataset_index(self,pkg_dict: dict[str, Any]):
        return pkg_dict
    
    
    # --- create ---   
    def create(self,entity: model.Package):
        pass
    
    # --- delete ---  
    def delete(self,entity: model.Package):
        pass
    
    # --- create ---
    def edit(self,entity: model.Package):
        pass        
        
    # --- READ ---      
    def read(self,entity: model.Package):
        pass

    
    
class SelloExcelenciaView(SingletonPlugin):
   
    implements(IBlueprint)
    implements(IConfigurer)
    
    log.info("[SelloExcelenciaView] Cargado con Exito")
    
    def update_config(self, config):
        
        log.info("[SelloResourcePlugin] update_config ejecutado")

        # Ruta absoluta de la carpeta templates de este plugin
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        #log.info(f"[SelloResourcePlugin] Buscando templates en: {template_path}")

        # Verificar que los archivos existan
        for root, dirs, files in os.walk(template_path):
            for f in files:
                log.info(f"[SelloResourcePlugin] Template detectado: {os.path.join(root, f)}")

      
        # Método oficial CKAN
        toolkit.add_template_directory(config, 'templates')

        # Método manual como respaldo
        if 'extra_template_paths' in config:
            config['extra_template_paths'] += ':' + template_path
        else:
            config['extra_template_paths'] = template_path
    
    def get_blueprint(self):    
        
        sello_bp = Blueprint("sello_excelencia", __name__, template_folder='templates')

        @sello_bp.route("/sello/listar")
        def listar_sellos():

            log.info("[SelloExcelenciaView] listar_sellos ejecutado")
            
            context = {'model': model, 'session': model.Session}
            
            # URL base del portal CKAN
            base_url = config.get('ckan.site_url', '').rstrip('/')
            log.info("[SelloExcelenciaView] base_url: %s", base_url)

            # Consultar todos los recursos PDF
            recursos = Session.query(Resource).filter(
                Resource.format.ilike('PDF')
            ).all()
       
            
            sellos = []
            
            for r in recursos:
                #print(r.id, r.name, r.format, r.url, r.extras)
                # Revisar si es un sello según el extra 'type'                
                extras = {}
                if r.extras:
                    if isinstance(r.extras, str):
                        try:
                            extras = json.loads(r.extras)
                        except Exception:
                            extras = {}                           
                    elif isinstance(r.extras, dict):
                        extras = r.extras
                        #log.info("[SelloExcelenciaView] listar_sellos extras dict Encontrado: %s", json.dumps(extras, indent=2, ensure_ascii=False))
                        
                if extras.get('type') != 'sello_excelencia':
                    continue

                # Construir nombre del archivo
                archivo = r.url.split('/')[-1] if r.url else ''
                url_descarga = f"{base_url}/dataset/{r.package_id}/resource/{r.id}/download/{archivo}"

                # Logs de depuración
                log.info("[SelloExcelenciaView] package_id: %s", r.package_id)
                log.info("[SelloExcelenciaView] resource_id: %s", r.id)
                log.info("[SelloExcelenciaView] archivo: %s", archivo)
                log.info("[SelloExcelenciaView] url_descarga: %s", url_descarga)
                    
                # Agregar a la lista
                sellos.append({
                    "id": r.id,
                    "package_id": r.package_id,
                    'title': r.name,
                    'description': r.description,
                    'pdf_url': url_descarga,
                    'fecha': r.created,
                    'categoria': extras.get('type', 'sello_excelencia')
                })
            
            # 🔹 Log completo de la lista sellos
            log.info("Lista completa de sellos: %s", sellos)

            return toolkit.render('sello/listar.html', {'sellos': sellos})
        
            
        @sello_bp.route('/sello/resource_form/<package_id>', methods=['GET', 'POST'])
        def new_sello_resource(package_id):            
    
            try:
                
                log.info("[SelloExcelenciaView] new_sello_resource ejecutado")
                
                # Obtener el dataset
                package = toolkit.get_action('package_show')(
                    {'ignore_auth': True},
                    {'id': package_id}
                )
                
                if not package:
                    h.flash_error("Dataset no encontrado")
                    return h.redirect_to('home.index')

                # Si es POST, CKAN ya valida automáticamente el CSRF
                if request.method == 'POST':
                    
                    context = {'model': model, 'session': model.Session, 'user': toolkit.c.user}
                    # 1️⃣ Recibir los textos
                    package_id = toolkit.request.form.get('package_id')
                    nombre = toolkit.request.form.get('name')
                    nombre_limpio = re.sub(r'\s+', '_', nombre.strip())
                    extension = toolkit.request.form.get('format')
                    description = toolkit.request.form.get('description')
                    
                    # 2️⃣ Recibir el archivo
                    archivo = toolkit.request.files.get('upload')
                    file_path = None
                
                    # 3️⃣ Aquí haces lo que necesites con los datos, por ejemplo:
                    
                    log.info("[SelloExcelenciaView] new_sello_resource Package ID:: %s", package_id)
                    log.info("[SelloExcelenciaView] new_sello_resource Nombre: %s", nombre)
                    log.info("[SelloExcelenciaView] new_sello_resource Extensión: %s", extension)
                    log.info("[SelloExcelenciaView] new_sello_resource Descripción: %s", description)                
                
                    package = toolkit.get_action('package_show')({'user': toolkit.c.user}, {'id': package_id})
                    
                    file_name = nombre_archivo = "{}.{}".format(nombre_limpio,extension)
                    
                    if archivo:
                        
                        nombre_archivo = archivo.filename
                        
                        #Crear Recurso
                        result = self.crear_sello_excelencia(package,file_name,archivo,context)
                        
                        #toolkit.h.flash_success("Recurso creado correctamente")
                        return toolkit.redirect_to('dataset_read', id=package_id)
                    
                # Si es GET, mostrar formulario
                return toolkit.render(
                    'sello/resource_form.html',
                    {
                        'package': package,
                        'csrf_field': h.csrf_input()
                    }
                )
            except ckan.logic.NotFound:
                # Handle the case where the package is not found
                h.flash_error("Dataset no encontrado")
                return h.redirect_to('home.index')

        # Intercepta la edición de datasets
        @sello_bp.app_context_processor
        def inject_sello_extras():

            log.info("[SelloExcelenciaView] injenject_sello_extras")
           
            if request.endpoint == 'dataset.edit':
                try:
                    
                    dataset_id = request.view_args.get('id')
                    pkg = model.Session.query(model.Package).options(joinedload(model.Package._extras)).filter_by(name=dataset_id).first()
                    extras_dict = {}
                    if pkg:
                        log.info("[SelloExcelenciaView] injenject_sello_extras pkg._extras: %s", pkg._extras)
                        for key, extra_obj in pkg._extras.items():
                            extras_dict[key] = extra_obj.value  # extra_obj.value es el valor que queremos
                        return dict(_extras=extras_dict)
                except Exception as e:                        
                    log.info("[SelloExcelenciaView] injenject_sello_extras pkg: %s", e)
                    return dict(_extras={})
            return dict()
            
        return sello_bp
    
    
    def crear_sello_excelencia(self, package,file_name,archivo,context):
        
        
        try:
            
            """
            Crea un recurso placeholder y luego actualiza con extras y datos reales.
            """

            package_id = package['id']
            
            data_dict = dict(toolkit.request.form)
            

            # 1 Crear Recurso
            resource_dict= {
                'package_id':package_id ,
                'name':data_dict.get('name'),
                'url':file_name,  # URL temporal,
                'format':data_dict.get('format'),
                'description':data_dict.get('description', '')
            }
           
            resource = toolkit.get_action('resource_create')(context, resource_dict)
           
            resource_id = resource['id']
            
            #log.info("[SelloExcelenciaView] crear_sello_excelencia resource_id: %s", resource_id)
            
            nuevo_nombre = resource_id[6:] 
            #log.info("[SelloExcelenciaView] crear_sello_excelencia nuevo_nombre: %s", nuevo_nombre)
                      
            # 2 Calcular ruta destino CKAN
            geojson_res_id = resource_id # UUID del recurso
            storage_path = toolkit.config.get('ckan.storage_path')
            subdir = os.path.join('resources',geojson_res_id[0:3], geojson_res_id[3:6]) # Creacion Arbol donde va a qUUID del recurso
            dest_dir = os.path.join(storage_path,subdir)
            os.makedirs(dest_dir, exist_ok=True)
            

            # 3 Guardar Archivo
            nuevo_nombre = resource_id[6:] 
            dest_path = os.path.join(dest_dir, nuevo_nombre)
            archivo.save(dest_path)

            # 4 Obtener size, last_modified y mimetype
            size = os.path.getsize(dest_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(dest_path))
            mimetype, encoding = mimetypes.guess_type(archivo.filename, strict=True)
            
            
            # 4 Actualizar URL y otros campos

            resource_dict = {
                'id': resource_id,
                'url_type': 'upload',
                'url':file_name,
                'size': size,
                'mimetype': mimetype,
                'last_modified': last_modified.isoformat()
            }
            
            updated_resource = toolkit.get_action('resource_update')(context, resource_dict)
    
            # 5 Marcar Etiqueta de Sello
            response=self.marcar_recurso_sello(resource_id)
            log.info("[SelloExcelenciaView] Recurso Creado con Exito")
            return True
        except Exception as e:
            log.info("[SelloExcelenciaView] Error al guardar el archivo: $s",e)           
            return  False

    def marcar_recurso_sello(self, resource_id):

        try:

            log.info("[SelloExcelenciaView] marcar_recurso_sello Ejecutado")

            # Obtener el recurso actual
            get_resource = toolkit.get_action('resource_show')
            resource = get_resource({'ignore_auth': True}, {'id': resource_id})

            # Agregar la bandera como campo plano (CKAN lo guarda en extras)
            resource['type'] = 'sello_excelencia'

            # Mantener datastore_active si existe
            if 'datastore_active' in resource:
                resource['datastore_active'] = resource['datastore_active']

            # Actualizar
            update_resource = toolkit.get_action('resource_update')
            update_resource({'ignore_auth': True}, resource)

            log.info("[SelloExcelenciaView] marcar_recurso_sello marca guardada con exito")

            return True
        except Exception as e:
            log.info("[SelloExcelenciaView] Error al guardar el archivo: $s",e)           
            return  False        
            
    def can_view(self, data_dict):
        return data_dict

    def setup_template_variables(self, context, data_dict):
        pass
        
    def view_template(self, context, data_dict):
        return 'sello_excelencia_view.html'

    def _get_sello_pdf(self, dataset_id):
        pass
        

