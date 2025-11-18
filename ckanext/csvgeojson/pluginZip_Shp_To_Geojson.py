# file: blueprints/ckan_proxy.py
from ckan.plugins import SingletonPlugin,implements,toolkit
from ckan.plugins.interfaces import  IConfigurer, IBlueprint
from flask import Blueprint, jsonify, redirect,request,Response,stream_with_context
import json, logging,os,  mimetypes, subprocess
import requests
from ckan.common import config
import time
import ckan.model as model
from ckanext.csvgeojson.services.zip_shp_to_geojson import Zip_Shp_JSONConverter
import ckan.lib.helpers as h
from flask import redirect


log = logging.getLogger(__name__)


class ApiZipShpToGeojsonView(SingletonPlugin):

    implements(IConfigurer)
    implements(IBlueprint)

    def update_config(self, config):
        log.info("[Api_Zip_Shp_To_GeojsonView] update_config ejecutado")

    
    def get_blueprint(self):

        ckan_shp_geojson_bp = Blueprint("Shp_GeoJson", __name__)

        log.info("[ApiZipShpToGeojsonView] get_blueprint ejecutado") 

        @ckan_shp_geojson_bp.route("/ckan/shp_to_geojson")
        def shp_to_geojson():

            organizations=Zip_Shp_JSONConverter.listar_organizaciones()
            datasets=Zip_Shp_JSONConverter.listar_dataset()

            log.info("[ApiZipShpToGeojsonView] shp_to_geojson ejecutado") 
            return toolkit.render('convertSHPToGeoJSOB.html',
                                    {
                                        'csrf_field': h.csrf_input(),
                                        'organizations':organizations,
                                        'datasets':datasets
                                    }
                                  )
           
          
        @ckan_shp_geojson_bp.route("/ckan/shp_to_geojson/convert",methods=['POST'])
        def convert_shp_geojson():

            log.info("[ApiZipShpToGeojsonView] convert_shp_geojson ejecutado") 
            
            archivo = toolkit.request.files.get('upload')  
            package_id=toolkit.request.form.get('dataset_org') 
            owner_org=toolkit.request.form.get('owner_org') 

            #log.info("[ApiZipShpToGeojsonView] convert_shp_geojson archivo=%s",archivo) 
            #log.info("[ApiZipShpToGeojsonView] convert_shp_geojson package_id=%s",package_id) 
            #log.info("[ApiZipShpToGeojsonView] convert_shp_geojson owner_org=%s",owner_org) 
           

            # Guardar archivo en /tmp
            tmp_path = f"/tmp/{archivo.filename}"
            archivo.save(tmp_path)   # <-- aquí ya tienes un string path válido

            filename=archivo.filename

            log_file = "/var/log/ckan/convert_job.log"

            # Lanzar proceso en background
            with open(log_file, "a") as f:
                subprocess.Popen(
                    [
                        "/usr/lib/ckan/default/bin/python",
                        "/usr/lib/ckan/default/src/ckan/ckanext/csvgeojson/convert_job.py",
                        tmp_path,
                        package_id,
                        owner_org,
                        filename
                    ],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    close_fds=True
                )

          
           

            return toolkit.h.redirect_to("Shp_GeoJson.shp_to_geojson")  # mensaje de "Procesando..."


        return ckan_shp_geojson_bp    
        