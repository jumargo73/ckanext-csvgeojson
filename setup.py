from setuptools import setup, find_packages

setup(
    name='ckanext-csvgeojson',
    version='0.1',
    description='Convierte CSV con coordenadas a GeoJSON para CKAN',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points='''
        [ckan.plugins]
        csv_to_geojson_api=ckanext.csvgeojson.plugin:CSVtoGeoJSONApiPlugin
        csv_to_geojson_dataset_resource=ckanext.csvgeojson.pluginDatasetResource:CSVtoGeoJSONDatasetResourcePlugin
    ''',
)
