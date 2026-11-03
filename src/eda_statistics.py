import os
import pandas as pd
import numpy as np
from scipy import stats

def perform_exploratory_data_analysis(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """
    Realiza un resumen de estadística descriptiva (media, mediana, desviación estándar,
    asimetría y curtosis) para las variables cuantitativas seleccionadas.
    Complejidad Temporal: O(N * K) donde N = municipios, K = variables.
    """
    print("\n" + "="*60)
    print("📊 RESUMEN ESTADÍSTICO EXPLORATORIO (EDA)")
    print("="*60)
    
    stats_dict = []
    for col in feature_cols:
        if col in df.columns:
            s = df[col].dropna()
            stats_dict.append({
                'Variable': col,
                'Media': np.mean(s),
                'Mediana': np.median(s),
                'Desv_Est': np.std(s, ddof=1),
                'Mínimo': np.min(s),
                'Máximo': np.max(s),
                'Asimetría (Skew)': stats.skew(s),
                'Curtosis': stats.kurtosis(s)
            })
            
    summary_df = pd.DataFrame(stats_dict)
    return summary_df

def run_anova_inter_state(df: pd.DataFrame, target_var: str = 'pct_vph_inter', state_col: str = 'cve_ent'):
    """
    Ejecuta una prueba ANOVA de un factor (One-Way ANOVA) para verificar si la media
    de la variable de conectividad varía significativamente entre Entidades Federativas.
    
    Hipótesis:
      - H0: mu_1 = mu_2 = ... = mu_32 (La penetración media de internet es igual en todos los estados)
      - H1: Al menos una entidad federativa tiene una penetración media distinta.
    """
    print("\n" + "="*60)
    print(f"🧪 PRUEBA DE HIPÓTESIS: ANOVA DE UN FACTOR PARA '{target_var}' POR ESTADO")
    print("="*60)
    
    # Agrupar datos por Entidad Federativa (primeros 2 dígitos de CVEGEO)
    df_clean = df.copy()
    if state_col not in df_clean.columns and 'cvegeo' in df_clean.columns:
        df_clean[state_col] = df_clean['cvegeo'].astype(str).str.zfill(5).str[:2]
        
    groups = [group[target_var].dropna().values for name, group in df_clean.groupby(state_col)]
    
    # Ejecutar F-test de ANOVA
    f_stat, p_value = stats.f_oneway(*groups)
    
    print(f"Número de Entidades Federativas analizadas: {len(groups)}")
    print(f"Estadístico F de Snedecor: {f_stat:.4f}")
    print(f"p-valor (p-value): {p_value:.4e}")
    
    alpha = 0.05
    if p_value < alpha:
        print("\n✅ DECISIÓN: Se rechaza la Hipótesis Nula (H0) con un nivel de confianza del 95%.")
        print("💡 CONCLUSIÓN: Existen diferencias estadísticamente significativas en la penetración")
        print("   de internet entre los estados de México, lo que justifica el modelado regionalizado.")
    else:
        print("\n❌ DECISIÓN: No se rechaza la Hipótesis Nula (H0).")
        print("   No hay evidencia suficiente de variabilidad entre entidades federativas.")

if __name__ == "__main__":
    # Dataset sintético de prueba basado en la estructura de 2,469 municipios
    np.random.seed(42)
    n_samples = 300
    
    mock_df = pd.DataFrame({
        'cvegeo': [f"{np.random.randint(1, 33):02d}{np.random.randint(1, 100):03d}" for _ in range(n_samples)],
        'pct_vph_inter': np.random.normal(loc=45.0, scale=18.0, size=n_samples).clip(0, 100),
        'pct_vph_pc': np.random.normal(loc=30.0, scale=15.0, size=n_samples).clip(0, 100),
        'pct_vph_cel': np.random.normal(loc=75.0, scale=12.0, size=n_samples).clip(0, 100)
    })
    
    features = ['pct_vph_inter', 'pct_vph_pc', 'pct_vph_cel']
    
    # 1. Ejecutar EDA
    eda_results = perform_exploratory_data_analysis(mock_df, features)
    print(eda_results.to_string(index=False))
    
    # 2. Ejecutar ANOVA
    run_anova_inter_state(mock_df, target_var='pct_vph_inter')