-- =============================================================================
-- PROYECTO INTEGRADOR: CLASIFICACIÓN DE RIESGO DE EXCLUSIÓN DIGITAL EN MÉXICO
-- Esquema Relacional en PostgreSQL
-- Llave Primaria Central: CVEGEO (5 dígitos: 2 Estado + 3 Municipio)
-- =============================================================================

-- Habilitar extensión PostGIS para operaciones geospaciales complejas (O(N log N))
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. DIMENSIÓN: Entidades Federativas
CREATE TABLE IF NOT EXISTS dim_entidad (
    cve_ent VARCHAR(2) PRIMARY KEY,
    nom_ent VARCHAR(100) NOT NULL
);

-- 2. DIMENSIÓN: Municipios (Tabla Maestra Geográfica)
CREATE TABLE IF NOT EXISTS dim_municipio (
    cvegeo VARCHAR(5) PRIMARY KEY,
    cve_ent VARCHAR(2) NOT NULL REFERENCES dim_entidad(cve_ent),
    cve_mun VARCHAR(3) NOT NULL,
    nom_mun VARCHAR(150) NOT NULL,
    pobtot INT NOT NULL CHECK (pobtot >= 0)
);

-- 3. HECHOS: Indicadores de Infraestructura TIC y Censo (INEGI 2020)
CREATE TABLE IF NOT EXISTS fact_censo_tic (
    cvegeo VARCHAR(5) PRIMARY KEY REFERENCES dim_municipio(cvegeo),
    vph_pc INT DEFAULT 0,       -- Viviendas con computadora
    vph_inter INT DEFAULT 0,    -- Viviendas con internet
    vph_cel INT DEFAULT 0,      -- Viviendas con celular
    pct_vph_inter NUMERIC(5,2), -- Porcentaje de cobertura de internet
    pct_vph_pc NUMERIC(5,2)
);

-- 4. HECHOS: Indicadores de Rezago Social (CONEVAL 2020)
CREATE TABLE IF NOT EXISTS fact_coneval_irs (
    cvegeo VARCHAR(5) PRIMARY KEY REFERENCES dim_municipio(cvegeo),
    poblacion_analfabeta NUMERIC(5,2),
    carencia_servicios_basicos NUMERIC(5,2),
    indice_rezago_social NUMERIC(8,4),
    grado_rezago_social VARCHAR(20)
);

-- 5. HECHOS: Rendimiento Real de Red (Ookla / IFT Q4-2020)
CREATE TABLE IF NOT EXISTS fact_calidad_red (
    cvegeo VARCHAR(5) PRIMARY KEY REFERENCES dim_municipio(cvegeo),
    avg_download_mbps NUMERIC(8,2),
    avg_upload_mbps NUMERIC(8,2),
    avg_latency_ms NUMERIC(8,2),
    total_tests INT DEFAULT 0
);

-- 6. TABLA CONSOLIDADA PARA MACHINE LEARNING (Target + Features)
CREATE TABLE IF NOT EXISTS ml_dataset_municipios (
    cvegeo VARCHAR(5) PRIMARY KEY REFERENCES dim_municipio(cvegeo),
    -- Features PCA y Entropía
    score_entropia NUMERIC(8,6),
    pca_component_1 NUMERIC(10,6),
    pca_component_2 NUMERIC(10,6),
    -- Etiqueta Target Multiclase: 0 = Bajo, 1 = Medio, 2 = Alto
    clase_riesgo_digital INT CHECK (clase_riesgo_digital IN (0, 1, 2)),
    fecha_proceso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ESTRATEGIA DE INDEXACIÓN (Complejidad B-Tree O(log N))
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_dim_mun_entidad ON dim_municipio(cve_ent);
CREATE INDEX IF NOT EXISTS idx_ml_clase_riesgo ON ml_dataset_municipios(clase_riesgo_digital);