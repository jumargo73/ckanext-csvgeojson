# file: blueprints/ckan_proxy.py
from ckan.plugins import SingletonPlugin,implements,toolkit
from ckan.plugins.interfaces import  IConfigurer, IBlueprint
from flask import Blueprint, jsonify, request,Response,stream_with_context
import json, logging,os,  mimetypes
import requests
from ckan.common import config
import time
import ckan.model as model

log = logging.getLogger(__name__)

# URL base del CKAN al que harás las consultas
#CKAN_BASE_URL = "https://datosabiertos.valledelcauca.gov.co"
CKAN_BASE_URL = "http://www.datosabiertos.valledelcauca.gov.co"

class ApiODataPluginView(SingletonPlugin):
   
    implements(IConfigurer)
    implements(IBlueprint)
    
    

    log.info("[ApiODataPluginView] Cargado con Exito")

   

    def update_config(self, config):
        log.info("[ApiODataPluginView] update_config ejecutado")
        
    
    def get_blueprint(self):

        ckan_proxy_bp = Blueprint("ckan_proxy", __name__)
        log.info("[ApiODataPluginView] get_blueprint ejecutado")


        @ckan_proxy_bp.route("/ckan-proxy/<resource_id>/query.json")
        def proxy_datastore(resource_id):
            """
            Devuelve tal cual la respuesta del API nativo de CKAN para que PowerBI lo consuma.
            """
            log.info("[ApiODataPluginView] proxy_datastore ejecutado")

            limit = request.args.get("limit", 50000)
            offset = request.args.get("offset", 0)

            context = {'model': model, 'session': model.Session,'user': toolkit.c.user or toolkit.config.get('ckan.site_id')}

            result = toolkit.get_action("datastore_search")(
                context,  # contexto
                {"resource_id": resource_id, "limit": limit, "offset": offset}
            )

            # Pasar solo los records o convertir a dict
            records_raw = result.get("records", [])

            # Convertir cada registro a dict puro
            records = [dict(r) for r in records_raw]

            #log.info("[CSVtoGeoJSONPlugin]  proxy_datastore, records: %s)", records)

            '''for r in records:
                print(type(r))'''

            #data = {"records": records}

            ##log.info("[CSVtoGeoJSONPlugin]  proxy_datastore, data: %s)", data)
            
            
            return json.dumps(records, ensure_ascii=False)
        
        return ckan_proxy_bp