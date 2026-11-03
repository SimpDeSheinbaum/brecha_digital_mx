import json
import os
import urllib.request
import ssl
import sqlalchemy as sa
import pandas as pd

os.makedirs("data", exist_ok=True)
ruta_municipios = os.path.join("data", "mexico_municipios.json")

print("⏳ Extrayendo registros geoestadísticos desde PostgreSQL 16...")

try:
    engine = sa.create_engine('postgresql+psycopg2://postgres:admin@localhost:5432/brecha_digital_db')
    
    # Inspección de columnas para evitar UndefinedColumn
    df_sample = pd.read_sql("SELECT * FROM v_reporte_brecha_digital LIMIT 1;", engine)
    cols = df_sample.columns.tolist()
    
    col_mun = "nom_mun" if "nom_mun" in cols else ("municipio" if "municipio" in cols else ("nombre_municipio" if "nombre_municipio" in cols else "cvegeo"))
    col_est = "estado" if "estado" in cols else ("entidad" if "entidad" in cols else "cve_ent")
    
    query = f"SELECT cvegeo, {col_est} AS estado, {col_mun} AS nom_mun FROM v_reporte_brecha_digital;"
    df = pd.read_sql(query, engine)
    df["cvegeo"] = df["cvegeo"].astype(str).str.zfill(5)
    df["cve_ent"] = df["cvegeo"].str[:2]
    print(f"✅ Ingesta SQL exitosa: {len(df):,} municipios encontrados.")
except Exception as e:
    print(f"⚠️ Advertencia consultando PostgreSQL 16: {e}")
    df = pd.DataFrame()

# URLs alternativas de alta disponibilidad para municipios de México
urls_muns = [
    "https://raw.githubusercontent.com/cartograd/mexico-geojson/master/mexico_municipios.json",
    "https://raw.githubusercontent.com/jorge-aguilera/mexico-geojson/master/municipios.json"
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

raw_geojson = None
for url in urls_muns:
    try:
        print(f"⏳ Intentando descargar GeoJSON desde fuente alternativa...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            raw_geojson = json.loads(response.read().decode('utf-8'))
            print("✅ GeoJSON municipal descargado correctamente.")
            break
    except Exception as e:
        print(f"⚠️ Falló descarga desde {url}: {e}")

if not raw_geojson:
    print("🛠️ Generando capa municipal sintética a partir de estados locales como respaldo...")
    ruta_estados = os.path.join("data", "mexico_estados.json")
    if os.path.exists(ruta_estados):
        with open(ruta_estados, "r", encoding="utf-8") as f:
            geojson_est = json.load(f)
        
        dicc_geometrias = {feat.get("properties", {}).get("name", "").strip(): feat.get("geometry") for feat in geojson_est.get("features", [])}
        
        features_respaldo = []
        for _, row in df.iterrows():
            cve_5digs = str(row["cvegeo"]).zfill(5)
            features_respaldo.append({
                "type": "Feature",
                "properties": {
                    "cvegeo": cve_5digs,
                    "CVEGEO": cve_5digs,
                    "cve_ent": cve_5digs[:2],
                    "name": str(row["nom_mun"]),
                    "estado": str(row["estado"])
                },
                "geometry": dicc_geometrias.get(str(row["estado"]).strip())
            })
        raw_geojson = {"type": "FeatureCollection", "features": features_respaldo}

mapa_muns = dict(zip(df["cvegeo"], zip(df["estado"], df["nom_mun"], df["cve_ent"]))) if not df.empty else {}

mapa_nombres_estados = {
    "Coahuila de Zaragoza": "Coahuila",
    "Michoacán de Ocampo": "Michoacán",
    "Veracruz de Ignacio de la Llave": "Veracruz",
    "Distrito Federal": "Ciudad de México"
}

features_optimizadas = []
for feat in raw_geojson.get("features", []):
    props = feat.get("properties", {})
    cvegeo = str(props.get("CVEGEO", props.get("cvegeo", props.get("CODIGO", "")))).zfill(5)
    
    if len(cvegeo) == 5:
        cve_ent_str = cvegeo[:2]
        info_sql = mapa_muns.get(cvegeo, (props.get("estado", ""), props.get("NOM_MUN", props.get("name", "")), cve_ent_str))
        estado_norm = mapa_nombres_estados.get(str(info_sql[0]), str(info_sql[0])).strip()

        feat["properties"] = {
            "cvegeo": cvegeo,
            "CVEGEO": cvegeo,
            "cve_ent": cve_ent_str,
            "CVE_ENT": cve_ent_str,
            "name": str(info_sql[1]),
            "estado": estado_norm
        }
        features_optimizadas.append(feat)

geojson_final = {
    "type": "FeatureCollection",
    "features": features_optimizadas
}

with open(ruta_municipios, "w", encoding="utf-8") as f:
    json.dump(geojson_final, f, ensure_ascii=False)

print(f"✅ ¡PROCESO CONCLUIDO! Capa municipal guardada en {ruta_municipios} con {len(features_optimizadas):,} municipios.")