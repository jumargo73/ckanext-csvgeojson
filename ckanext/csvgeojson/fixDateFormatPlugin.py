from ckan.plugins import SingletonPlugin, IResourceController
import sqlalchemy as sa

class FixDateFormatPlugin(SingletonPlugin):
    implements(IResourceController)

    def after_update(self, context, resource):
        connection = context['model'].Session.connection()
        query = sa.text("""
            UPDATE resource_view
            SET config = REPLACE(config::text, '"date_format": "%d/%m/%Y"', '"date_format": "llll"')
            WHERE resource_id = :rid
                AND ( config::text LIKE '%"date_format": "%d/%m/%Y"%'
                    OR config::text LIKE '%"date_format": "%d-%m-%Y"%'
                );
        """)
        connection.execute(query, {'rid': resource['id']})