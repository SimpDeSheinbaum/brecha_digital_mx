import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def calculate_shannon_entropy(df: pd.DataFrame, feature_cols: list) -> pd.Series:
    """
    Calcula el peso por Entropía de Shannon para medir el grado de incertidumbre/variabilidad
    de la infraestructura digital por municipio.
    Complejidad Temporal: O(N * K) donde N = municipios, K = variables.
    """
    # Copia y normalización min-max para evitar valores negativos
    data = df[feature_cols].copy()
    data_norm = (data - data.min()) / (data.max() - data.min() + 1e-9)
    
    # Proporción p_ij
    p_ij = data_norm.div(data_norm.sum(axis=0), axis=1) + 1e-9
    
    # Entropía E_j por variable
    k = 1.0 / np.log(len(df))
    E_j = -k * (p_ij * np.log(p_ij)).sum(axis=0)
    
    # Diversidad d_j y pesos w_j
    d_j = 1.0 - E_j
    w_j = d_j / d_j.sum()
    
    # Puntaje final ponderado por Entropía por municipio
    entropy_score = (data_norm * w_j).sum(axis=1)
    return entropy_score

def apply_pca_transformation(df: pd.DataFrame, feature_cols: list, n_components: int = 2):
    """
    Aplica Análisis de Componentes Principales (PCA) para reducir la correlación
    entre variables sociodemográficas y de infraestructura TIC.
    """
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df[feature_cols].fillna(0))
    
    pca = PCA(n_components=n_components, random_state=42)
    pca_features = pca.fit_transform(scaled_data)
    
    explained_var = pca.explained_variance_ratio_.sum()
    print(f" Variance Explicada Acumulada por los {n_components} componentes: {explained_var:.2%}")
    
    pca_df = pd.DataFrame(
        pca_features, 
        columns=[f'pca_component_{i+1}' for i in range(n_components)],
        index=df.index
    )
    return pca_df

if __name__ == "__main__":
    # Prueba unitaria local
    mock_data = pd.DataFrame({
        'cvegeo': ['01001', '09002', '15101'],
        'pct_vph_inter': [65.4, 82.1, 41.2],
        'pct_vph_pc': [45.2, 68.0, 22.1],
        'pct_vph_cel': [88.1, 92.4, 71.0]
    })
    
    cols = ['pct_vph_inter', 'pct_vph_pc', 'pct_vph_cel']
    
    # 1. Calcular Entropía
    mock_data['score_entropia'] = calculate_shannon_entropy(mock_data, cols)
    
    # 2. Aplicar PCA
    pca_res = apply_pca_transformation(mock_data, cols, n_components=2)
    mock_data = pd.concat([mock_data, pca_res], axis=1)
    
    print("\n--- Resultados de Feature Engineering (PCA + Entropía) ---")
    print(mock_data[['cvegeo', 'score_entropia', 'pca_component_1', 'pca_component_2']])