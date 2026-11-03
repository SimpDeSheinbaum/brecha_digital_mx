import warnings
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import classification_report, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GridSearchCV, train_test_split
import xgboost as xgb

warnings.filterwarnings('ignore')

def optimize_xgboost_for_high_recall(X: pd.DataFrame, y: pd.Series):
    """
    Realiza una búsqueda de hiperparámetros (GridSearchCV) orientada a maximizar
    el Recall Macro y minimizar Falsos Negativos en la clase de Riesgo Alto (2).
    
    Complejidad Temporal: O(K_folds * N_combinations * T * D * N log N)
    """
    print("\n" + "="*65)
    print("🎯 OPTIMIZACIÓN DE HIPERPARÁMETROS (XGBOOST + GRIDSEARCHCV)")
    print("="*65)
    
    # 1. División estratificada
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # 2. Balanceo de Clases con SMOTE sobre datos de entrenamiento
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    
    # 3. Definición del modelo base XGBoost
    xgb_base = xgb.XGBClassifier(
        objective='multi:softprob',
        eval_metric='mlogloss',
        random_state=42
    )
    
    # 4. Malla de Hiperparámetros orientada a evitar Sobreajuste y priorizar Sensibilidad
    param_grid = {
        'n_estimators': [100, 150],
        'max_depth': [3, 4, 5],            # Profundidad moderada para evitar memorización
        'learning_rate': [0.03, 0.05, 0.1], # Tasa de aprendizaje controlada
        'subsample': [0.8, 1.0],            # Muestreo estocástico de filas
        'colsample_bytree': [0.8, 1.0]     # Muestreo estocástico de características
    }
    
    # 5. Búsqueda con Validación Cruzada (Stratified 5-Fold) priorizando Recall Macro
    grid_search = GridSearchCV(
        estimator=xgb_base,
        param_grid=param_grid,
        scoring='recall_macro',
        cv=5,
        n_jobs=-1,
        verbose=1
    )
    
    print("⏳ Ejecutando GridSearchCV (5-Fold CV optimizando Recall Macro)...")
    grid_search.fit(X_train_res, y_train_res)
    
    best_model = grid_search.best_estimator_
    print(f"\n✅ Mejores Hiperparámetros Encontrados:")
    for param, val in grid_search.best_params_.items():
        print(f"   • {param}: {val}")
        
    # 6. Evaluación sobre el Conjunto de Prueba Prístino (Test)
    y_pred = best_model.predict(X_test)
    
    recall_macro = recall_score(y_test, y_pred, average='macro')
    f1_macro = f1_score(y_test, y_pred, average='macro')
    
    print("\n" + "-"*45)
    print("📊 RESULTADOS DEL MODELO OPTIMIZADO EN TEST")
    print("-"*45)
    print(f"🎯 Recall Macro (Prioridad Cero Falsos Negativos): {recall_macro:.4f}")
    print(f"📈 F1-Score Macro: {f1_macro:.4f}\n")
    
    cm = confusion_matrix(y_test, y_pred)
    print("Matriz de Confusión:")
    print(cm)
    
    # Cálculo explícito de Falsos Negativos en Riesgo Alto (Clase 2)
    falsos_negativos_alto = cm[2, 0] + cm[2, 1]
    print(f"\n⚠️ Falsos Negativos en Riesgo Alto (Clase 2 -> 0 o 1): {falsos_negativos_alto} municipios")
    
    print("\nReporte de Clasificación Detallado:")
    print(classification_report(y_test, y_pred, target_names=['Bajo (0)', 'Medio (1)', 'Alto (2)']))

if __name__ == "__main__":
    np.random.seed(42)
    n_samples = 600
    
    # Reutilización de la matriz X y generación estocástica de Y con ruido
    X_mock = pd.DataFrame({
        'pct_vph_inter': np.random.normal(45, 15, n_samples).clip(0, 100),
        'pct_vph_pc': np.random.normal(30, 12, n_samples).clip(0, 100),
        'score_entropia': np.random.uniform(0, 1, n_samples),
        'pca_comp_1': np.random.normal(0, 1, n_samples),
        'pca_comp_2': np.random.normal(0, 1, n_samples)
    })
    
    latent_score = (
        0.5 * X_mock['pct_vph_inter'] + 
        0.3 * X_mock['pct_vph_pc'] + 
        20.0 * X_mock['score_entropia'] + 
        np.random.normal(0, 10, n_samples)
    )
    
    y_mock = pd.Series(
        np.select(
            [latent_score > 55, latent_score > 35],
            [0, 1],
            default=2
        )
    )
    
    optimize_xgboost_for_high_recall(X_mock, y_mock)