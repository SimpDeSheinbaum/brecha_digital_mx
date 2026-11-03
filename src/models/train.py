import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, recall_score, f1_score
from imblearn.over_sampling import SMOTE
import xgboost as xgb

def train_and_evaluate_multiclass_models(X: pd.DataFrame, y: pd.Series):
    """
    Entrena y evalúa modelos de clasificación multiclase (Random Forest vs XGBoost)
    aplicando balanceo con SMOTE para minimizar Falsos Negativos en Riesgo Alto.
    
    Complejidad Temporal Entrenamiento: O(M * K * N log N) donde M = árboles, K = features, N = municipios.
    """
    print("\n" + "="*60)
    print("🤖 ENTRENAMIENTO DE MODELOS MULTICLASE (SMOTE + ENSEMBLES)")
    print("="*60)
    
    # 1. División estratificada (Train / Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    print(f"Distribución original de clases en Train:\n{y_train.value_counts().to_dict()}")
    
    # 2. Balanceo de Clases con SMOTE
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    
    print(f"Distribución tras balanceo SMOTE en Train:\n{y_train_res.value_counts().to_dict()}")
    
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced'),
        "XGBoost": xgb.XGBClassifier(n_estimators=100, learning_rate=0.1, random_state=42, eval_metric='mlogloss')
    }
    
    for model_name, clf in models.items():
        print("\n" + "-"*40)
        print(f"🌲 Entrenando: {model_name}")
        print("-"*40)
        
        # Entrenamiento
        clf.fit(X_train_res, y_train_res)
        y_pred = clf.predict(X_test)
        
        # Evaluación de Métricas Críticas
        recall_macro = recall_score(y_test, y_pred, average='macro')
        f1_macro = f1_score(y_test, y_pred, average='macro')
        
        print(f"🎯 Recall Macro (Prioridad Cero Falsos Negativos): {recall_macro:.4f}")
        print(f"📈 F1-Score Macro: {f1_macro:.4f}\n")
        print("Matriz de Confusión:")
        print(confusion_matrix(y_test, y_pred))
        print("\nReporte de Clasificación Detallado:")
        print(classification_report(y_test, y_pred, target_names=['Bajo (0)', 'Medio (1)', 'Alto (2)']))

if __name__ == "__main__":
    np.random.seed(42)
    n_samples = 600
    
    # Matriz de entradas X con colinealidad y variabilidad simulada
    X_mock = pd.DataFrame({
        'pct_vph_inter': np.random.normal(45, 15, n_samples).clip(0, 100),
        'pct_vph_pc': np.random.normal(30, 12, n_samples).clip(0, 100),
        'score_entropia': np.random.uniform(0, 1, n_samples),
        'pca_comp_1': np.random.normal(0, 1, n_samples),
        'pca_comp_2': np.random.normal(0, 1, n_samples)
    })
    
    # Ponderación estocástica (con ruido) para simular traslape real entre municipios
    latent_score = (
        0.5 * X_mock['pct_vph_inter'] + 
        0.3 * X_mock['pct_vph_pc'] + 
        20.0 * X_mock['score_entropia'] + 
        np.random.normal(0, 10, n_samples)  # Ruido ambiental de telecom
    )
    
    # Asignación multiclase ordinal (0: Bajo, 1: Medio, 2: Alto) con desbalance real
    y_mock = pd.Series(
        np.select(
            [latent_score > 55, latent_score > 35],
            [0, 1],
            default=2
        )
    )
    
    # Ejecutar pipeline de entrenamiento con SMOTE y Ensembles
    train_and_evaluate_multiclass_models(X_mock, y_mock)