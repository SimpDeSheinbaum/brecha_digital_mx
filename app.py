import streamlit as st
import pandas as pd
import sqlalchemy as sa
import plotly.express as px
import json
import os

# ==============================================================================
# 1. CONFIGURACIÓN DE PANTALLA Y MODO OSCURO POR DEFAULT
# ==============================================================================
st.set_page_config(
    page_title="IFT / SEDATU - Visor Geográfico de Exclusión Digital",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de Estilos Fijos
bg_color = "#0e1117"
sidebar_bg = "#161b22"
text_color = "#ffffff"
subtext_color = "#9ca3af"
border_color = "#374151"
card_bg = "#1f2937"

# Máquina de Estados para la Navegación LOD
if "nivel_view" not in st.session_state:
    st.session_state.nivel_view = "NACIONAL"
if "estado_sel" not in st.session_state:
    st.session_state.estado_sel = "Todos los Estados"
if "municipio_sel" not in st.session_state:
    st.session_state.municipio_sel = "Todos los Municipios"

# ==============================================================================
# 2. PANEL LATERAL DE CONFIGURACIÓN (SIDEBAR)
# ==============================================================================
st.sidebar.title("🎛️ Configuración IFT")

st.sidebar.subheader("📊 Métrica Proyectada")
metrica_sel = st.sidebar.radio(
    "Selecciona Variable:",
    ["% Probabilidad Riesgo (XGBoost)", "% Viviendas sin Internet (INEGI)"],
    index=0
)

st.sidebar.markdown("---")

st.sidebar.subheader("🤖 Sensibilidad IFT")
umbral_p = st.sidebar.slider(
    "Umbral de Decisión (p)",
    min_value=0.30,
    max_value=0.60,
    value=0.40,
    step=0.05,
    help="Ajusta el umbral p para priorizar municipios vulnerables y minimizar Falsos Negativos (FN)."
)

# ==============================================================================
# 3. INYECCIÓN CSS: MODO OSCURO Y SUPRESIÓN DE RUNNERS NATIVOS
# ==============================================================================
st.markdown(f"""
    <style>
        html, body, [data-testid="stAppViewContainer"], .main {{
            background-color: {bg_color} !important;
        }}
        
        .main .block-container {{
            padding-top: 0.8rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
            background-color: {bg_color} !important;
        }}
        
        header[data-testid="stHeader"], [data-testid="stToolbar"], footer, [data-testid="stStatusWidget"], div[st-eval-status], .stStatusWidget {{
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
            opacity: 0 !important;
        }}
        
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
            border-right: 1px solid {border_color} !important;
            display: flex !important;
            visibility: visible !important;
            width: 310px !important;
        }}
        
        [data-testid="stSidebar"] * {{
            color: {text_color} !important;
        }}
        
        .stPlotlyChart {{
            width: 100% !important;
            height: 60vh !important;
            background-color: transparent !important;
        }}

        .metric-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 14px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}

        .metric-value {{
            font-size: 1.55rem;
            font-weight: 700;
            color: #27ae60;
        }}

        .metric-title {{
            font-size: 0.85rem;
            color: {subtext_color};
            margin-top: 4px;
        }}

        .loader-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 55vh;
            width: 100%;
        }}

        .loader-card {{
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: {sidebar_bg};
            border: 1px solid {border_color};
            border-radius: 14px;
            padding: 22px 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }}

        .radar-pulse {{
            width: 20px;
            height: 20px;
            background-color: #27ae60;
            border-radius: 50%;
            margin-right: 18px;
            box-shadow: 0 0 0 rgba(39, 174, 96, 0.7);
            animation: pulse 1.6s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(39, 174, 96, 0.7); }}
            70% {{ transform: scale(1.35); box-shadow: 0 0 0 16px rgba(39, 174, 96, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(39, 174, 96, 0); }}
        }}

        .loader-text {{ color: {text_color}; font-size: 1.1rem; font-weight: 500; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. CAPA DE EXTRACCIÓN CACHEADA (POSTGRESQL 16 & GEOJSON)
# ==============================================================================
@st.cache_data(ttl=600)
def cargar_datos_postgres():
    engine = sa.create_engine('postgresql+psycopg2://postgres:admin@localhost:5432/brecha_digital_db')
    query = "SELECT * FROM v_reporte_brecha_digital;"
    df = pd.read_sql(query, engine)
    df["cvegeo"] = df["cvegeo"].astype(str).str.zfill(5)
    df["cve_ent"] = df["cvegeo"].str[:2]
    col_mun = "nom_mun" if "nom_mun" in df.columns else ("municipio" if "municipio" in df.columns else "cvegeo")
    df["nom_mun"] = df[col_mun]
    return df

@st.cache_data(ttl=3600)
def cargar_geojson_estados():
    ruta = os.path.join("data", "mexico_estados.json")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        mapa_nombres = {
            "Coahuila de Zaragoza": "Coahuila",
            "Michoacán de Ocampo": "Michoacán",
            "Veracruz de Ignacio de la Llave": "Veracruz",
            "Distrito Federal": "Ciudad de México"
        }
        for feature in geojson_data.get("features", []):
            nombre_orig = feature["properties"].get("name", "")
            feature["properties"]["name"] = mapa_nombres.get(nombre_orig, nombre_orig).strip()
        return geojson_data
    return None

@st.cache_data(ttl=3600)
def cargar_geojson_municipios():
    ruta = os.path.join("data", "mexico_municipios.json")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                if "cvegeo" in props:
                    props["cvegeo"] = str(props["cvegeo"]).zfill(5)
                    props["CVEGEO"] = props["cvegeo"]
                elif "CVEGEO" in props:
                    props["CVEGEO"] = str(props["CVEGEO"]).zfill(5)
                    props["cvegeo"] = props["CVEGEO"]
            return data
    return None

placeholder_loader = st.empty()
with placeholder_loader.container():
    st.markdown("""
        <div class="loader-wrapper">
            <div class="loader-card">
                <div class="radar-pulse"></div>
                <div class="loader-text">
                    📡 Sincronizando capas geoestadísticas y clasificando N = 2,471 municipios (IFT / INEGI 2020)...
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

try:
    df = cargar_datos_postgres()
    geojson_estados = cargar_geojson_estados()
    geojson_municipios = cargar_geojson_municipios()
    placeholder_loader.empty()
    st.sidebar.success(f"✅ PostgreSQL 16: {len(df):,} municipios.")
except Exception as e:
    placeholder_loader.empty()
    st.error(f"❌ Error al conectar a PostgreSQL 16: {e}")
    st.stop()

# ==============================================================================
# 5. TRANSFORMACIÓN Y ASIGNACIÓN DE MÉTRICAS DINÁMICAS
# ==============================================================================
df["estatus_prioridad_dinamico"] = df["probabilidad_alto_riesgo"].apply(
    lambda p: "PRIORITARIO_IFT" if p >= umbral_p else "MONITOREO_ORDINARIO"
)
df["pct_sin_internet"] = 100.0 - df["pct_vph_inter"]

diccio_nombres_inegi = {
    "Coahuila de Zaragoza": "Coahuila",
    "Michoacán de Ocampo": "Michoacán",
    "Veracruz de Ignacio de la Llave": "Veracruz",
    "Distrito Federal": "Ciudad de México"
}
df["estado"] = df["estado"].replace(diccio_nombres_inegi).str.strip()

col_mapa_mun = "probabilidad_alto_riesgo" if metrica_sel == "% Probabilidad Riesgo (XGBoost)" else "pct_sin_internet"
label_mapa = "% Riesgo Promedio" if metrica_sel == "% Probabilidad Riesgo (XGBoost)" else "% Viviendas sin Internet"

paleta_semaforo = [
    [0.0, "#27ae60"],
    [0.25, "#2ecc71"],
    [0.50, "#f1c40f"],
    [0.70, "#e67e22"],
    [0.85, "#e74c3c"],
    [1.0, "#900c3f"]
]

# ==============================================================================
# 6. ENCABEZADO Y BARRA DE NAVEGACIÓN DINÁMICA
# ==============================================================================
col_nav1, col_nav2 = st.columns([2, 1])

with col_nav1:
    lista_estados = ["Todos los Estados"] + sorted(df["estado"].unique().tolist())
    
    # Calcular índice actual según st.session_state
    idx_est = 0
    if st.session_state.estado_sel in lista_estados:
        idx_est = lista_estados.index(st.session_state.estado_sel)

    est_sel = st.selectbox("Selecciona Entidad Federativa", lista_estados, index=idx_est)
    
    if est_sel != st.session_state.estado_sel:
        st.session_state.estado_sel = est_sel
        if est_sel == "Todos los Estados":
            st.session_state.nivel_view = "NACIONAL"
            st.session_state.municipio_sel = "Todos los Municipios"
        else:
            st.session_state.nivel_view = "ESTATAL"
            st.session_state.municipio_sel = "Todos los Municipios"
        st.rerun()

    # Si estamos dentro de un Estado, habilitar el selector secundario de Municipios
    if st.session_state.nivel_view in ["ESTATAL", "MUNICIPAL"]:
        df_est_curr = df[df["estado"] == st.session_state.estado_sel]
        lista_muns = ["Todos los Municipios"] + sorted(df_est_curr["nom_mun"].unique().tolist())
        
        idx_mun = 0
        if st.session_state.municipio_sel in lista_muns:
            idx_mun = lista_muns.index(st.session_state.municipio_sel)

        mun_sel = st.selectbox(f"Selecciona Municipio ({st.session_state.estado_sel}):", lista_muns, index=idx_mun)
        
        if mun_sel != st.session_state.municipio_sel:
            st.session_state.municipio_sel = mun_sel
            st.session_state.nivel_view = "MUNICIPAL" if mun_sel != "Todos los Municipios" else "ESTATAL"
            st.rerun()

with col_nav2:
    if st.session_state.nivel_view in ["ESTATAL", "MUNICIPAL"]:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("⬅️ Regresar al Mapa Nacional", use_container_width=True):
            st.session_state.nivel_view = "NACIONAL"
            st.session_state.estado_sel = "Todos los Estados"
            st.session_state.municipio_sel = "Todos los Municipios"
            st.rerun()

# Subtítulo Dinámico
if st.session_state.nivel_view == "NACIONAL":
    sub_title = "Ámbito: <b>Nivel Nacional (32 Entidades)</b>"
elif st.session_state.nivel_view == "ESTATAL":
    sub_title = f"Ámbito: <b>Nivel Estatal: {st.session_state.estado_sel}</b>"
else:
    sub_title = f"Ámbito: <b>Municipio: {st.session_state.municipio_sel} ({st.session_state.estado_sel})</b>"

st.markdown(f"""
    <div style="text-align: center; margin-bottom: 5px;">
        <h2 style="color: {text_color}; margin: 0; padding: 0; font-size: 1.35rem;">
            Diagnóstico Geográfico de Exclusión Digital en México (IFT / SEDATU)
        </h2>
        <p style="color: {subtext_color}; margin: 2px 0 0 0; font-size: 0.9rem;">
            {sub_title} | Métrica: <b>{label_mapa}</b> | Umbral IFT: <b>p &ge; {umbral_p:.2f}</b>
        </p>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 7. MOTOR CARTOGRÁFICO DE ALTA VELOCIDAD Y HOVER MINIMALISTA
# ==============================================================================
color_borde_hd = "#ffffff"

if st.session_state.nivel_view == "NACIONAL":
    df_estado_agg = df.groupby(["cve_ent", "estado"]).agg(
        prob_riesgo=("probabilidad_alto_riesgo", lambda x: x.mean() * 100),
        pct_sin_inter=("pct_sin_internet", "mean"),
    ).reset_index()
    
    col_mapa = "prob_riesgo" if metrica_sel == "% Probabilidad Riesgo (XGBoost)" else "pct_sin_inter"
    df_estado_agg[col_mapa] = df_estado_agg[col_mapa].fillna(15.0)
    
    fig = px.choropleth(
        df_estado_agg,
        geojson=geojson_estados,
        locations="estado",
        featureidkey="properties.name",
        color=col_mapa,
        color_continuous_scale=paleta_semaforo,
        range_color=(10, 85),
        labels={"estado": "Estado"}
    )
    
    # Hover Minimalista: Muestra únicamente el Nombre del Estado
    fig.update_traces(
        hovertemplate="<b>%{location}</b><extra></extra>",
        marker_line_width=0.8,
        marker_line_color=color_borde_hd
    )

elif st.session_state.nivel_view in ["ESTATAL", "MUNICIPAL"]:
    df_sub = df[df["estado"] == st.session_state.estado_sel].copy()
    df_sub["val_plot"] = df_sub[col_mapa_mun] * 100 if metrica_sel == "% Probabilidad Riesgo (XGBoost)" else df_sub[col_mapa_mun]
    cve_ent_activa = df_sub["cve_ent"].iloc[0]
    
    if st.session_state.nivel_view == "MUNICIPAL":
        df_sub_render = df_sub[df_sub["nom_mun"] == st.session_state.municipio_sel]
    else:
        df_sub_render = df_sub

    geojson_sub_mun = {"type": "FeatureCollection", "features": []}
    if geojson_municipios:
        for feat in geojson_municipios.get("features", []):
            props = feat.get("properties", {})
            cve_feat = str(props.get("cve_ent", props.get("CVE_ENT", props.get("cvegeo", "")[:2]))).zfill(2)
            nom_est = props.get("estado", "")
            
            if cve_feat == cve_ent_activa or nom_est == st.session_state.estado_sel:
                if st.session_state.nivel_view == "MUNICIPAL":
                    if props.get("name") == st.session_state.municipio_sel or props.get("cvegeo") == df_sub_render["cvegeo"].iloc[0]:
                        geojson_sub_mun["features"].append(feat)
                else:
                    geojson_sub_mun["features"].append(feat)

    fig = px.choropleth(
        df_sub_render,
        geojson=geojson_sub_mun if len(geojson_sub_mun["features"]) > 0 else geojson_estados,
        locations="cvegeo" if len(geojson_sub_mun["features"]) > 0 else "estado",
        featureidkey="properties.cvegeo" if len(geojson_sub_mun["features"]) > 0 else "properties.name",
        color="val_plot",
        color_continuous_scale=paleta_semaforo,
        range_color=(10, 90),
        labels={"val_plot": label_mapa, "nom_mun": "Municipio"},
        hover_data=["nom_mun", "poblacion_total", "estatus_prioridad_dinamico"]
    )
    
    fig.update_traces(
        marker_line_width=0.8,
        marker_line_color=color_borde_hd
    )

fig.update_geos(
    fitbounds="locations",
    visible=False,
    projection_type="mercator",
    bgcolor="rgba(0,0,0,0)"
)

fig.update_layout(
    height=520,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    coloraxis_colorbar=dict(
        title=label_mapa,
        title_font=dict(color=text_color, size=10),
        tickfont=dict(color=text_color, size=9),
        x=0.94,
        len=0.80,
        thickness=14
    )
)

st.plotly_chart(
    fig, 
    use_container_width=True,
    config={
        'scrollZoom': False,
        'doubleClick': False,
        'displayModeBar': False,
        'showAxisDragHandles': False
    }
)

# ==============================================================================
# 8. PANEL DE DATOS RELEVANTES CALCULADOS POR EL MODELO (DEBAJO DEL MAPA)
# ==============================================================================
st.markdown("---")

if st.session_state.nivel_view == "NACIONAL":
    total_muns = len(df)
    muns_prioritarios = (df["estatus_prioridad_dinamico"] == "PRIORITARIO_IFT").sum()
    pct_prioritarios = (muns_prioritarios / total_muns) * 100.0
    pob_impactada = df[df["estatus_prioridad_dinamico"] == "PRIORITARIO_IFT"]["poblacion_total"].sum()
    prom_riesgo_nac = df["probabilidad_alto_riesgo"].mean() * 100.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_muns:,}</div>
                <div class="metric-title">Total Municipios Evaluados</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #e74c3c;">{muns_prioritarios:,} ({pct_prioritarios:.1f}%)</div>
                <div class="metric-title">Municipios de Alta Vulnerabilidad (p &ge; {umbral_p:.2f})</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #f1c40f;">{pob_impactada:,.0f}</div>
                <div class="metric-title">Población en Riesgo Digital Crítico</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{prom_riesgo_nac:.1f}%</div>
                <div class="metric-title">Probabilidad de Exclusión Promedio Nacional</div>
            </div>
        """, unsafe_allow_html=True)

elif st.session_state.nivel_view == "ESTATAL":
    df_est = df[df["estado"] == st.session_state.estado_sel]
    total_est_muns = len(df_est)
    est_prioritarios = (df_est["estatus_prioridad_dinamico"] == "PRIORITARIO_IFT").sum()
    est_pob_vulnerable = df_est[df_est["estatus_prioridad_dinamico"] == "PRIORITARIO_IFT"]["poblacion_total"].sum()
    prom_riesgo_est = df_est["probabilidad_alto_riesgo"].mean() * 100.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_est_muns}</div>
                <div class="metric-title">Municipios en {st.session_state.estado_sel}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #e74c3c;">{est_prioritarios}</div>
                <div class="metric-title">Municipios Prioritarios IFT</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #f1c40f;">{est_pob_vulnerable:,.0f}</div>
                <div class="metric-title">Población Estatal Vulnerable</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{prom_riesgo_est:.1f}%</div>
                <div class="metric-title">Riesgo Promedio de la Entidad</div>
            </div>
        """, unsafe_allow_html=True)

else:
    df_mun = df[(df["estado"] == st.session_state.estado_sel) & (df["nom_mun"] == st.session_state.municipio_sel)].iloc[0]
    
    p_mun = df_mun["probabilidad_alto_riesgo"] * 100.0
    estatus_mun = df_mun["estatus_prioridad_dinamico"]
    color_estatus = "#e74c3c" if estatus_mun == "PRIORITARIO_IFT" else "#27ae60"
    pob_mun = df_mun["poblacion_total"]
    sin_inter_mun = df_mun["pct_sin_internet"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{p_mun:.1f}%</div>
                <div class="metric-title">Probabilidad Riesgo (XGBoost)</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {color_estatus};">{estatus_mun}</div>
                <div class="metric-title">Estatus de Prioridad IFT</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{pob_mun:,.0f}</div>
                <div class="metric-title">Población Total (INEGI 2020)</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{sin_inter_mun:.1f}%</div>
                <div class="metric-title">Viviendas Sin Internet</div>
            </div>
        """, unsafe_allow_html=True)