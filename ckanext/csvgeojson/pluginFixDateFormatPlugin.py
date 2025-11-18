from ckan.plugins import SingletonPlugin, IResourceController,implements
import sqlalchemy as sa
import logging
from ckan.types import Context 
from typing import Any

log = logging.getLogger(__name__)

class FixDateFormatPlugin(SingletonPlugin):
    implements(IResourceController)

    log.info("[pluginFixDateFormatPlugin] FixDateFormatPlugin Cargado con Exito")
    
    
    # --- resource_create ---        
    def before_resource_create(self,context: Context, resource: dict[str, Any]):
        pass
        
    def after_resource_create(self,context: Context, resource: dict[str, Any]):
        pass
        
    
    def before_resource_update(self,context: Context, current: dict[str, Any], resource: dict[str, Any]):
        pass


    def after_resource_update(self, context, resource):

        log.info("[pluginFixDateFormatPlugin] after_update ejecutado") 
        connection = context['model'].Session.connection()
        query = sa.text("""
            UPDATE resource_view
            SET config = REGEXP_REPLACE(
                config::text,
                '"date_format": "%d[/-]%m[/-]%Y"',
                '"date_format": "llll"',
                'g'
            )
            WHERE resource_id = :rid
            AND config::text ~ '"date_format": "%d[/-]%m[/-]%Y"';                    
        """)
        connection.execute(query, {'rid': resource['id']})
        context['model'].Session.commit()

    def before_resource_delete(self,context: Context, resource: dict[str, Any], resources: list[dict[str, Any]]):
        pass

    def after_resource_delete(self,context: Context, resources: list[dict[str, Any]]):
        pass    

    def before_resource_show(self,resource_dict: dict[str, Any]):
        return resource_dict

    def before_dataset_show(self,context: Context, pkg_dict: dict[str, Any]):
        return pkg_dict