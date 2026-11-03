import os
import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2

def load_processed_data_to_postgres(csv_path: str, db_url: str):
    """
    Realiza la carga masiva (Bulk Insert) de la base procesada de municipios
    a PostgreSQL, garantizando la integridad referencial de la llave primaría CVEGEO.
    
    Complejidad Temporal: O(N) para la carga secuencial en la tabla dim_municipio.
    """
    print(f"⏳ Cargando datos procesados desde '{csv_path}' hacia PostgreSQL...")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ El archivo '{csv_path}' no existe. Ejecuta primero ingest_real_data.py")
        
    # Leer CSV garantizando el tipo cadena en las claves
    df = pd.read_csv(csv_path, dtype={'cvegeo': str, 'cve_ent': str, 'cve_mun': str})
    
    # Relleno preventivo de ceros a la izquierda (LPAD/zfill a 5 dígitos)
    df['cvegeo'] = df['cvegeo'].str.zfill(5)
    
    engine = create_engine(db_url)
    
    try:
        with engine.begin() as connection:
            print("💾 Insertando registros en la tabla 'dim_municipio'...")
            
            # Carga a tabla temporal o directa
            df.to_sql(
                name='dim_municipio',
                con=connection,
                if_exists='append',  # O 'replace' según el diseño de pruebas
                index=False,
                chunksize=500
            )
            
            # Validación de la inserción mediante consulta SQL
            result = connection.execute(text("SELECT COUNT(*) FROM dim_municipio;"))
            total_records = result.scalar()
            
            print(f"✅ Carga masiva exitosa. Total de municipios registrados en PostgreSQL: {total_records}")
            
    except Exception as e:
        print(f"❌ Error durante la inserción en PostgreSQL: {e}")

if __name__ == "__main__":
    # Configuración de variables de conexión
    DB_USER = "postgres"
    DB_PASS = "admin"
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "brecha_digital_db"
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    PROCESSED_CSV = os.path.join("data", "censo_2020_processed.csv")
    
    # Descomentar para ejecutar cuando el servidor de PostgreSQL esté activo:
    # load_processed_data_to_postgres(PROCESSED_CSV, DATABASE_URL)