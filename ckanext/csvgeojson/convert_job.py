import geopandas as gpd
import json, logging,os,  mimetypes,zipfile,tempfile,sys,shutil
from datetime import datetime
import ckan.lib.helpers as h
from ckanapi import RemoteCKAN
from configparser import ConfigParser
from ckan.common import config
from ckan.plugins import toolkit
from ckanapi.errors import NotFound
import time
import certifi, requests

logging.basicConfig(
    filename="/var/log/ckan/convert_job.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger(__name__)

def get_ckan_config():

    log.info("[convert_job] get_ckan_config ejecutado")
    
    
    # Ruta a tu production.ini
    ini_path = "/etc/ckan/default/produccion.ini"  # cámbiala según tu instalación
    storage_path = '/var/lib/ckan/default/'

    config_ckan = ConfigParser()
    config_ckan.read(ini_path)

    # CKAN guarda las variables en la sección [app:main]
    site_url = config_ckan.get("app:main", "ckan.site_url", fallback=None)
    api_key = config_ckan.get("app:main", "ckan.datapusher.api_token", fallback=None)
    ssl_cert = config_ckan.get("app:main", "ckan.devserver.ssl_cert", fallback=None)
   
    
    #api_key = os.environ.get("CKAN_API_KEY")  # mejor manejarlo como variable de entorno

    log.info("[get_ckan_config] site_url: %s", site_url)
    log.info("[get_ckan_config] api_key: %s", api_key)
    log.info("[get_ckan_config] storage_path: %s", storage_path)
    log.info("[get_ckan_config] ssl_cert: %s", ssl_cert)
    
    return site_url, api_key,storage_path,ssl_cert


def shp_to_csv(shp_path, output_path=None, drop_geometry=False):
    
    try:
            
        """
        Convierte un SHP en CSV.
        - shp_path: ruta del archivo .shp
        - output_path: ruta donde guardar el CSV
        - drop_geometry: si True elimina geometría
        """
        log.info("[convert_job] shp_to_csv ejecutado [Generando Archivo]")
        # Leer SHP
        gdf = gpd.read_file(shp_path)

        # Definir salida
        if not output_path:
            output_path = os.path.splitext(shp_path)[0] + ".csv"

        if drop_geometry:
            # Sin geometría → solo atributos
            df = gdf.drop(columns="geometry")
            df.to_csv(output_path, index=False)
        else:
            # Mantener geometría como WKT
            gdf.to_csv(output_path, index=False)
        #log.info("[convert_job] shp_to_csv output_path=%s",output_path)
        return output_path
    except Exception as e:
            log.info("[convert_job] Error: %s",e)   

def shp_to_csv_points(shp_path, output_path=None):

    log.info("[convert_job] shp_to_csv_points ejecutado")
    gdf = gpd.read_file(shp_path)

    # Extraer lat/lon si es de puntos
    if gdf.geom_type.isin(["Point"]).all():
        gdf["lon"] = gdf.geometry.x
        gdf["lat"] = gdf.geometry.y
        gdf = gdf.drop(columns="geometry")

    if not output_path:
        output_path = os.path.splitext(shp_path)[0] + ".csv"

    gdf.to_csv(output_path, index=False)
    return output_path

def ensure_resource_exists(ckan, resource_id, retries=5, wait=3):
    """
    Verifica si el recurso existe en CKAN, reintenta si aún no está disponible.
    """
    for intento in range(retries):
        try:
            resource = ckan.action.resource_show(id=resource_id)
            log.info("[ensure_resource_exists] Recurso encontrado: %s", resource["id"])
            return resource
        except NotFound:
            log.warning("[ensure_resource_exists] Recurso %s no encontrado. Reintento %s/%s",
                        resource_id, intento + 1, retries)
            time.sleep(wait)
        except Exception as e:
            log.error("[ensure_resource_exists] Error inesperado: %s", e, exc_info=True)
            raise

    raise Exception(f"Recurso {resource_id} no disponible tras {retries} intentos")


def update_resource_exists(ckan, resource_id, size, last_modified,mimetype,output_path,dataset_name,retries=5, wait=3):
    """
    Actualiza el recurso en CKAN, reintenta si aún no está disponible.
    """
    for i in range(retries):
        try:
            resource = ckan.action.resource_update(
                id=resource_id,
                name=os.path.basename(output_path),
                mimetype= mimetype,
                format="CSV",
                url=os.path.splitext(dataset_name)[0] + ".csv",   
                size=size,
                last_modified=last_modified.isoformat()
            )
            log.info("[update_resource_exists] Recurso Actualizado: %s", resource_id)
            return resource
        except Exception as e:
            print(f"[WARN] Intento {i+1}/{retries} falló: {e}")
            time.sleep(wait)

    raise Exception(f"Recurso {resource_id} no actualizado tras {retries} intentos")


def main():
    
    try:
        
        # sys.argv[0] = convert_job.py
        if len(sys.argv) < 5:
            log.error("Parámetros insuficientes. Esperados: zip_path, None, package_id, owner_org,filename")
            sys.exit(1)

        zip_path = sys.argv[1]      # Ruta al archivo zip o shp    
        package_id = sys.argv[2]   # ID del dataset
        owner_org = sys.argv[3]    # Organización
        dataset_name=sys.argv[4]       # nombre archivo
        output_path = None       # Ese 'None' que mandas

        log.info("=== Iniciando job de conversión SHP → GeoJSON ===")
        #log.info("[main] Archivo: %s", zip_path)
        #log.info("[main] Package ID: %s", package_id)
        #log.info("[main] Owner Org: %s", owner_org)
        #log.info("[main] dataset_name: %s", dataset_name)
        
        site_url, api_key,storage_path,ssl_cert = get_ckan_config()

        log.info("[main] site_url: %s", site_url)
        log.info("[main] api_key: %s", api_key)
        log.info("[main] storage_path: %s", storage_path)
        log.info("[main] ssl_cert: %s", ssl_cert)

        session = requests.Session()
        session.verify = certifi.where() 

        ckan = RemoteCKAN(site_url, apikey=api_key,session=session)
        #ckan1 = RemoteCKAN(site_url, apikey=api_key,verify=ssl_cert)

        # Crear carpeta temporal
        with tempfile.TemporaryDirectory() as tmpdir:

            #zip_path = os.path.join(tmpdir, filename)

            #log.info("[convert_job] zip_shp_to_geojson zip_path=%s",zip_path)

            # Guardar el ZIP subido en el directorio temporal
            #archivo.save(zip_path)
            
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
                #log.info("[convert_job] No se encontró ningún .shp dentro del ZIP")
                h.flash_error("Error: No se encontró ningún .shp dentro del ZIP")
            
            
            #log.info("[convert_job] zip_shp_to_geojson shp_file=%s",shp_file)
            
            output_path=shp_to_csv(shp_file, None, False)

            log.info("[convert_job] shp_to_csv ejecutado [Archivo Generando con Archivo]")

            resource = ckan.action.resource_create(
                package_id=package_id,
                name=os.path.basename(output_path),
                format="CSV",
                url=os.path.splitext(dataset_name)[0] + ".csv",         # marcador interno que dice “es un recurso subido”
                url_type="upload"     # explícitamente indica que es un recurso local
            
            )

            log.info(f"Resource Creado: {resource['id']}")


            #log.info("[convert_job] zip_shp_to_geojson resource create: %s", json.dumps(resource, indent=2, ensure_ascii=False))

            #Guardar el Recurso    
            resource_id = resource['id']
            
            #log.info("[convert_job] zip_shp_to_geojson resource_id=%s",resource_id)

            
            nuevo_nombre = resource_id[6:] 

            #log.info("[convert_job] zip_shp_to_geojson nuevo_nombre=%s",nuevo_nombre)

                    
            

            # 2 Calcular ruta destino CKAN
            geojson_res_id = resource_id # UUID del recurso
        
            subdir = os.path.join('resources',geojson_res_id[0:3], geojson_res_id[3:6]) # Creacion Arbol donde va a qUUID del recurso
            dest_dir = os.path.join(storage_path,subdir)
            os.makedirs(dest_dir, exist_ok=True)
            

            # 3 Guardar Archivo
            nuevo_nombre = resource_id[6:] 
            dest_path = os.path.join(dest_dir, nuevo_nombre)
            
            if dataset_name is not None:
                shutil.move(output_path, dest_path)
                
            #log.info("[convert_job] zip_shp_to_geojson dest_path=%s",dest_path)

            # 4 Obtener size, last_modified y mimetype
            size = os.path.getsize(dest_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(dest_path))
            mimetype, encoding = mimetypes.guess_type(output_path, strict=True)
            
            resource_existe = ensure_resource_exists(ckan, resource_id)

            # Crear vista geoespacial si aplica
            view = ckan.action.resource_view_create(
                resource_id=resource_existe["id"],
                view_type="datatables_view",
                title="DataTable"
            )

            log.info(f"Vista creada: {view['id']}")

            resource=update_resource_exists(ckan, resource_existe["id"],size, last_modified,mimetype,output_path,dataset_name)
            log.info(f"Resource Actualizado: {resource['id']}")

            # Limpieza del temporal
            shutil.rmtree(tmpdir)

        log.info("[convert_job] zip_shp_to_geojson GeoJSON generado en: %s", output_path)

    except Exception as e:
            log.info("[convert_job] Error: %s",e)     
    
if __name__ == "__main__":
    main()
