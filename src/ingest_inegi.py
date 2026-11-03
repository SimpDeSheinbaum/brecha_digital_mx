import pandas as pd
import numpy as np

def clean_inegi_cvegeo(df: pd.DataFrame, state_col: str = 'ENTIDAD', mun_col: str = 'MUN') -> pd.DataFrame:
    """
    Formatea las columnas de Entidad y Municipio para garantizar una clave CVEGEO de 5 dígitos.
    Complejidad Temporal: O(N) sobre el número de filas del dataset.
    """
    df_clean = df.copy()
    
    # 1. Asegurar formato de texto y rellenar ceros a la izquierda (LPAD)
    # 2 dígitos para estado (ej. '01'), 3 dígitos para municipio (ej. '001')
    df_clean[state_col] = df_clean[state_col].astype(str).str.zfill(2)
    df_clean[mun_col] = df_clean[mun_col].astype(str).str.zfill(3)
    
    # 2. Generar llave primaria CVEGEO (5 dígitos)
    df_clean['cvegeo'] = df_clean[state_col] + df_clean[mun_col]
    
    # 3. Validar integridad referencial (no deben existir claves de longitud distinta de 5)
    invalid_keys = df_clean[df_clean['cvegeo'].str.len() != 5]
    if not invalid_keys.empty:
        raise ValueError(f"Se encontraron {len(invalid_keys)} registros con CVEGEO inválida.")
        
    return df_clean

if __name__ == "__main__":
    # Prueba unitaria local para verificar el funcionamiento correcto
    sample_data = pd.DataFrame({
        'ENTIDAD': [1, 9, 15],
        'MUN': [1, 2, 101],
        'NOM_MUN': ['Aguascalientes', 'Azcapotzalco', 'Ecatepec de Morelos'],
        'POBTOT': [948990, 432205, 1645352]
    })
    
    df_result = clean_inegi_cvegeo(sample_data)
    print("--- Prueba de Integridad de CVEGEO ---")
    print(df_result[['cvegeo', 'NOM_MUN', 'POBTOT']])