from ckan.plugins import SingletonPlugin, IDatasetForm, implements, IPackageController, IResourceController
from ckan.plugins import toolkit
from ckan.plugins.interfaces import IResourceView, IConfigurer, IBlueprint
from flask import Blueprint,request
import json, logging,os,  mimetypes
from datetime import datetime
import ckan.logic as logic
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
            package = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
            
            
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

         # Archivos estáticos (public)
        public_path = os.path.join(os.path.dirname(__file__), "public")
        #log.info(f"[SelloResourcePlugin] Buscando images en: {public_path}")

        # Verificar que los archivos existan
        for root, dirs, files in os.walk(template_path):
            for f in files:
                log.info(f"[SelloResourcePlugin] Template detectado: {os.path.join(root, f)}")

        # Verificar que los archivos existan
        for root, dirs, files in os.walk(public_path):
            for f in files:
                log.info(f"[SelloResourcePlugin] Imagenes detectadas: {os.path.join(root, f)}")
      
        # Método oficial CKAN
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

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
            
            '''context = {'user': toolkit.c.user or toolkit.config.get('ckan.site_id')}

            #log.info("[SelloExcelenciaView] context: %s", json.dumps(context, indent=2, ensure_ascii=False))

            # aquí validas si tiene permisos, por ejemplo acceso admin a dataset
            try: 
                toolkit.check_access('package_update', context)
                log.info("[SelloExcelenciaView] Con Acceso")
                can_edit = True
            except logic.NotAuthorized:
                log.info("[SelloExcelenciaView] Sin acceso")
                can_edit = False'''

            can_edit = True    
            log.info("[SelloExcelenciaView] acceso: true")

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
                        log.info("[SelloExcelenciaView] listar_sellos extras dict Encontrado: %s", json.dumps(extras, indent=2, ensure_ascii=False))

                

                '''if extras.get('type') != 'sello_excelencia':
                    continue'''

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
                    'categoria': extras.get('type'),
                    'fecha_obtencion': extras.get('fecha_obtencion'),
                    'dependiencia': extras.get('owner_org'),
                    'nivel': extras.get('nivel')
                })
            
            # ---------------------------
            # Paginación
            # ---------------------------
            per_page = 10  # cantidad de sellos por página
            page = int(request.args.get("page", 1))  # ?page=2
            total = len(sellos)

            # calcular inicio y fin
            start = (page - 1) * per_page
            end = start + per_page

            # recorte de la lista
            sellos_paginados = sellos[start:end]

            # total de páginas
            total_pages = (total + per_page - 1) // per_page
                    
            # 🔹 Log completo de la lista sellos
            log.info("Lista completa de sellos: %s", sellos)

            return toolkit.render('sello/listar.html', {'sellos': sellos_paginados,'page':page,'total_pages':total_pages, 'can_edit': can_edit})

        @sello_bp.route('/sello/edit/<id>')
        def sello_edit(id):

            
            log.info("[sello_excelencia] sello_edit Ejecutado") 
           
            # 🔹 Log completo de la lista sellos
            log.info("[sello_excelencia] sello_edit id: %s", id)

            context = {'model': model, 'session': model.Session,'user': toolkit.c.user or toolkit.config.get('ckan.site_id')}
            
            organizations=self.listar_organizaciones()

            log.info("[sello_excelencia] sello_edit organizations: %s", json.dumps(organizations, indent=2, ensure_ascii=False))
           
 
            sello = self.get_sello(id,context)  # lógica de obtener el recurso
            
            log.info("[sello_excelencia] sello_edit sello: %s", sello)

            extras = {}
            if sello.extras:
                if isinstance(sello.extras, str):
                    try:
                        extras = json.loads(sello.extras)
                    except Exception:
                        extras = {}                           
                elif isinstance(sello.extras, dict):
                    extras = sello.extras
            
            log.info("[SelloExcelenciaView] listar_sellos extras dict Encontrado: %s", json.dumps(extras, indent=2, ensure_ascii=False))

            package = toolkit.get_action('package_show')(
                    context,
                    {'id': sello.package_id}
                )
            
            log.info("[sello_excelencia] sello_edit package: %s", json.dumps(package, indent=2, ensure_ascii=False))
                        
            log.info("[sello_excelencia] sello_edit organizacion_id: %s", package['organization']['id'])
            
            entidad = toolkit.get_action('organization_show')(
                    context,
                    {'id': package['organization']['id']}
                )

            log.info("[sello_excelencia] sello_edit organization: %s", json.dumps(entidad, indent=2, ensure_ascii=False))
              

            # Si es GET, mostrar formulario
            return toolkit.render(
                'sello/resource_form.html',
                {
                    'package': package,
                    'csrf_field': h.csrf_input(),
                    'organizations':organizations,
                    'resource':sello,
                    'entidad':entidad,
                    'extras':extras
                }
            )

        @sello_bp.route('/sello/update/<id>', methods=['POST'])   
        def update_sello_resource(id):

            context = {'model': model, 'session': model.Session, 'user': toolkit.c.user}
            # 1️⃣ Recibir los textos
            package_id = toolkit.request.form.get('package_id')
            nombre = toolkit.request.form.get('name')
            nombre_limpio = re.sub(r'\s+', '_', nombre.strip())
            extension = toolkit.request.form.get('format')
            description = toolkit.request.form.get('description')
            owner_org = toolkit.request.form.get('owner_org')
            fecha_obtencion = toolkit.request.form.get('fecha_obtencion')
            nivel = toolkit.request.form.get('nivel')
            
            # 2️⃣ Recibir el archivo
            archivo = toolkit.request.files.get('upload')
            file_path = None
        
            # 3️⃣ Aquí haces lo que necesites con los datos, por ejemplo:
            
            log.info("[SelloExcelenciaView] update_sello_resource Package ID:: %s", package_id)
            log.info("[SelloExcelenciaView] update_sello_resource Nombre: %s", nombre)
            log.info("[SelloExcelenciaView] update_sello_resource Extensión: %s", extension)
            log.info("[SelloExcelenciaView] update_sello_resource Descripción: %s", description)
            log.info("[SelloExcelenciaView] update_sello_resource owner_org: %s", owner_org) 
            log.info("[SelloExcelenciaView] update_sello_resource fecha_obtencion: %s", fecha_obtencion)   
            log.info("[SelloExcelenciaView] update_sello_resource nivel: %s", nivel)                   
        
            resource = toolkit.get_action('resource_show')({'user': toolkit.c.user}, {'id': id})
            package = toolkit.get_action('package_show')({'user': toolkit.c.user}, {'id': resource['package_id']})
            
            organizacion = toolkit.get_action('organization_show')({'user': toolkit.c.user}, {'id': owner_org})
            
            file_name=None

            nombre_archivo = "{}.{}".format(nombre_limpio,extension)
            
            
            if archivo:
                file_name = nombre_archivo = "{}.{}".format(nombre_limpio,extension)
                #nombre_archivo = archivo.filename

                # 1 Crear Recurso
                resource_dict= {
                    'package_id':package['id'] ,
                    'name':nombre,
                    'url':file_name,  # URL temporal,
                    'format':extension,
                    'description':description
                }
            else:
                # 1 Crear Recurso
                resource_dict= {
                    'package_id':package['id'] ,
                    'name':nombre,
                    'url':nombre_archivo,  # URL temporal,                    
                    'format':extension,
                    'description':description
                }

            log.info("[SelloExcelenciaView] update_sello_resource resource_dict: %s", resource_dict)
            
            #Crear Recurso
            result = self.save_sello_excelencia(resource_dict,file_name,archivo,context,organizacion,resource)
            
            #toolkit.h.flash_success("Recurso creado correctamente")
            return toolkit.redirect_to(toolkit.h.url_for('sello_excelencia.listar_sellos'))
                

            

        
        @sello_bp.route('/sello/delete/<id>', methods=['POST'])
        def sello_delete(id):

            context = {
                "model": model,
                "session": model.Session,
                "user": toolkit.c.user  # usuario actual
            }

            data_dict = {"id": id}

            try:
                toolkit.get_action("resource_delete")(context, data_dict)
                toolkit.h.flash_success("Recurso eliminado correctamente.")
            except toolkit.ObjectNotFound:
                toolkit.h.flash_error("El recurso no existe.")
            except toolkit.NotAuthorized:
                toolkit.h.flash_error("No tienes permisos para eliminar este recurso.")

            return toolkit.redirect_to(toolkit.h.url_for("sello_excelencia.listar_sellos"))         
            
            
        
        @sello_bp.route('/sello/resource_form/<package_id>', methods=['GET', 'POST'])
        def new_sello_resource(package_id):            
    
            try:
                
                log.info("[SelloExcelenciaView] new_sello_resource ejecutado")
                
                # Obtener el dataset
                package = toolkit.get_action('package_show')(
                    {'ignore_auth': True},
                    {'id': package_id}
                )


                organizations=self.listar_organizaciones()
                
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
                    owner_org = toolkit.request.form.get('owner_org')
                    fecha_obtencion = toolkit.request.form.get('fecha_obtencion')
                    nivel = toolkit.request.form.get('nivel')
                    
                    # 2️⃣ Recibir el archivo
                    archivo = toolkit.request.files.get('upload')
                    file_path = None
                
                    # 3️⃣ Aquí haces lo que necesites con los datos, por ejemplo:
                    
                    log.info("[SelloExcelenciaView] new_sello_resource Package ID:: %s", package_id)
                    log.info("[SelloExcelenciaView] new_sello_resource Nombre: %s", nombre)
                    log.info("[SelloExcelenciaView] new_sello_resource Extensión: %s", extension)
                    log.info("[SelloExcelenciaView] new_sello_resource Descripción: %s", description)
                    log.info("[SelloExcelenciaView] new_sello_resource owner_org: %s", owner_org) 
                    log.info("[SelloExcelenciaView] new_sello_resource fecha_obtencion: %s", fecha_obtencion)   
                    log.info("[SelloExcelenciaView] new_sello_resource nivel: %s", nivel)                   
                
                  

                    package = toolkit.get_action('package_show')({'user': toolkit.c.user}, {'id': package_id})
                    organizacion = toolkit.get_action('organization_show')({'user': toolkit.c.user}, {'id': owner_org})
                    
                    
                    
                    if archivo:

                        file_name = nombre_archivo = "{}.{}".format(nombre_limpio,extension)
                        #nombre_archivo = archivo.filename

                        # 1 Crear Recurso
                        resource_dict= {
                            'package_id':package['id'] ,
                            'name':nombre,
                            'url':file_name,  # URL temporal,
                            'format':extension,
                            'description':description
                        }

                        log.info("[SelloExcelenciaView] new_sello_resource resource_dict: %s", resource_dict)
                        
                       
                        
                        #Crear Recurso
                        result = self.save_sello_excelencia(resource_dict,file_name,archivo,context,organizacion)
                        
                        #toolkit.h.flash_success("Recurso creado correctamente")
                        return toolkit.redirect_to(toolkit.h.url_for('sello_excelencia.listar_sellos'))
                      
                    
                # Si es GET, mostrar formulario
                return toolkit.render(
                    'sello/resource_form.html',
                    {
                        'package': package,
                        'csrf_field': h.csrf_input(),
                        'organizations':organizations
                    }
                )
            except logic.NotFound:
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
    


    def get_sello(self, id,context):

        resource = Session.query(Resource).filter(
            Resource.format.ilike('PDF'),
            Resource.id == id
        ).first()
        #resource = toolkit.get_action('resource_show')(context, {'id': id})
        return resource

    def sello_edit(self, id,context):
        resource = toolkit.get_action('resource_show')(context, {'id': id})
        return resource
        


    def sello_delete(self, id,context):
        resource = toolkit.get_action('resource_delete')(context, {'id': id})
        return resource

    
    def save_sello_excelencia(self, resource_dict,file_name,archivo,context,organizacion,resource=None):
        
        
        try:
            
            """
            Crea un recurso placeholder y luego actualiza con extras y datos reales.
            """

            #package_id = package['id']
            
            #data_dict = dict(toolkit.request.form)

            # 1 Crear Recurso
            '''resource_dict= {
                'package_id':package_id ,
                'name':data_dict.get('name'),
                'url':file_name,  # URL temporal,
                'format':data_dict.get('format'),
                'description':data_dict.get('description')
            }'''


            if resource:
                # Actualizar recurso existente
                resource_dict["id"] = resource["id"]
                action = "resource_update"
                resource = toolkit.get_action('resource_update')(context, resource_dict)
                log.info("[SelloExcelenciaView] save_sello_excelencia resource update: %s", json.dumps(resource, indent=2, ensure_ascii=False))

            else:
                # Crear nuevo recurso
                action = "resource_create"
            
                resource = toolkit.get_action('resource_create')(context, resource_dict)
                log.info("[SelloExcelenciaView] save_sello_excelencia create: %s", json.dumps(resource, indent=2, ensure_ascii=False))

           
            
            
            
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
            
            if file_name is not None:
                archivo.save(dest_path)


            # 4 Obtener size, last_modified y mimetype
            size = os.path.getsize(dest_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(dest_path))
            mimetype, encoding = mimetypes.guess_type(archivo.filename, strict=True)
            
            
            # 1. Obtener el recurso completo
            #resource = toolkit.get_action('resource_show')(context, {'id': resource_id})

            # 5. Actualizar solo los campos que quieras cambiar
            resource['url_type'] = 'upload'
            resource['size'] = size
            resource['mimetype'] = mimetype
            resource['last_modified'] = last_modified.isoformat()

            # 6 Actualizar URL y otros campos

            '''resource_dict = {
                'id': resource_id,
                'url_type': 'upload',
                'url':file_name,
                'size': size,
                'mimetype': mimetype,
                'last_modified': last_modified.isoformat()
            }'''
            
            
            # 6. Mandar el recurso completo a update
            updated_resource = toolkit.get_action('resource_update')(context, resource)
            #updated_resource = toolkit.get_action('resource_update')(context, resource_dict)

            log.info("[SelloExcelenciaView] save_sello_excelencia resource update 1: %s", json.dumps(updated_resource, indent=2, ensure_ascii=False))

    
            # 5 Marcar Etiqueta de Sello
            response=self.marcar_recurso_sello(resource_id,organizacion)
            log.info("[SelloExcelenciaView] Recurso Guardado con Exito")
            return True
        except Exception as e:
            log.info("[SelloExcelenciaView] Error al guardar el archivo: $s",e)           
            return  False

    def marcar_recurso_sello(self, resource_id,organizacion):

        try:

            log.info("[SelloExcelenciaView] marcar_recurso_sello Ejecutado")

            # El context suele incluir al usuario (puede ser sysadmin)
            context = {
                'model': model,
                'session': model.Session,
                'user': toolkit.c.user  # o el nombre de un usuario válido
            }

            # Obtener el recurso actual
            get_resource = toolkit.get_action('resource_show')            
            resource = get_resource({'ignore_auth': True}, {'id': resource_id})

            log.info("[SelloExcelenciaView] marcar_recurso_sello resource show: %s", resource)


            #owner_org = toolkit.request.form.get('owner_org')
            #organizacion = toolkit.get_action('organization_show')(context, {'id': owner_org})
        
            fecha_obtencion = toolkit.request.form.get('fecha_obtencion')
            nivel = toolkit.request.form.get('nivel')


            # Agregar la bandera como campo plano (CKAN lo guarda en extras)
            resource['type'] = 'sello_excelencia'
            resource['fecha_obtencion'] = fecha_obtencion
            resource['nivel'] = nivel
            resource['owner_org'] = organizacion['title']
            

            # Mantener datastore_active si existe
            if 'datastore_active' in resource:
                resource['datastore_active'] = resource['datastore_active']

            # Actualizar
            update_resource = toolkit.get_action('resource_update')
            update_resource({'ignore_auth': True}, resource)

            log.info("[SelloExcelenciaView] marcar_recurso_sello resource update: %s", update_resource)


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

    def listar_organizaciones(self):
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
        

  
