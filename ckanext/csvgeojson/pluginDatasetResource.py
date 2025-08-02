from ckan.plugins import SingletonPlugin, implements, IPackageController, IBlueprint,IResourceController
from ckan.plugins.toolkit import get_action,check_access, ValidationError,c
from flask import Blueprint, request, jsonify
from shapely.geometry import Point, mapping
import json, tempfile, logging,os, shutil, time, mimetypes
from datetime import datetime
import ckan.model as model
from ckan.types import ActionResult, Context, DataDict, Query, Schema 
from typing import (Container, Optional,
                    Union, Any, cast, Type)
from ckanext.csvgeojson.services.geojson_converter import GeoJSONConverter


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
        pass
     
    
    # --- resource_update ---    

    def before_resource_update(self,context: Context, current: dict[str, Any], resource: dict[str, Any]):
        pass

    def after_resource_update(self, context, resource):
        
        log.info("[CSVtoGeoJSONPlugin] after_resource_update ejecutado")
        # Procesar solo CSV
        if resource.get('format', '').lower() != 'csv':
            return

        
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
        pass
        
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
        
     