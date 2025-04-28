import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --- Configuración de la página ---
st.set_page_config(page_title="🚀 Dashboard Implementadores", layout="wide", page_icon="🚀")

# --- Estilos globales y espaciado ---
st.markdown("""
    <style>
        header, footer { visibility: hidden; }
        .block-container { padding: 1rem 2rem; }
        .plotly-graph-div { margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- Login personalizado ---
USERS = {"admin": "secret123", "user": "pass456"}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔒 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if USERS.get(username) == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# --- Usuario autenticado ---
st.sidebar.success(f"Usuario: **{st.session_state.user}**")
st.title("🚀 Dashboard de Desempeño de Implementadores")

# --- Carga de datos desde archivo local ---
try:
    df = pd.read_excel('datos.xlsx')
    df.columns = df.columns.str.strip()
except Exception as e:
    st.error(f"❌ Error al leer 'datos.xlsx': {e}")
    st.stop()

# --- Validar columnas necesarias ---
required_cols = ['Implementador', 'Fecha Llegada a Revisión']
if not all(col in df.columns for col in required_cols):
    st.error(f"❌ El archivo debe contener las columnas: {required_cols}")
    st.stop()

# --- Preprocesamiento de fechas ---
df['Fecha Llegada a Revisión'] = pd.to_datetime(df['Fecha Llegada a Revisión'], errors='coerce')
df.dropna(subset=['Fecha Llegada a Revisión'], inplace=True)

# --- Filtros en Sidebar ---
st.sidebar.header("🎛️ Filtros")
implementadores = sorted(df['Implementador'].unique())
sel_impl = st.sidebar.multiselect("Implementadores", implementadores, default=implementadores)
df = df[df['Implementador'].isin(sel_impl)]

# Rango de fechas
date_min = df['Fecha Llegada a Revisión'].dt.date.min()
date_max = df['Fecha Llegada a Revisión'].dt.date.max()
fecha_inicio, fecha_fin = st.sidebar.slider(
    "Rango de fechas", value=(date_min, date_max), min_value=date_min, max_value=date_max, format="DD/MM/YYYY"
)
df = df[(df['Fecha Llegada a Revisión'].dt.date >= fecha_inicio) & (df['Fecha Llegada a Revisión'].dt.date <= fecha_fin)]

# --- Notificaciones en tiempo real ---
today = pd.Timestamp(datetime.now().date())
vencidas = df[df['Fecha Llegada a Revisión'] < today]
proximas = df[(df['Fecha Llegada a Revisión'] >= today) & (df['Fecha Llegada a Revisión'] <= today + pd.Timedelta(days=3))]
if not vencidas.empty:
    st.warning(f"⚠️ Tareas vencidas: {len(vencidas)}")
if not proximas.empty:
    st.info(f"⏰ Tareas próximas a vencer (3 días): {len(proximas)}")

# --- Preparar datos agregados ---
# Total por implementador
cnt = df['Implementador'].value_counts().reset_index()
cnt.columns = ['Implementador', 'Tareas']

# Evolución mensual
df['Mes'] = df['Fecha Llegada a Revisión'].dt.to_period('M').astype(str)
mes = df.groupby('Mes').size().reset_index(name='Tareas')

# Comparativa anual
df['Año'] = df['Fecha Llegada a Revisión'].dt.year
anual = df.groupby(['Año', 'Implementador']).size().reset_index(name='Tareas')

# Pivot para heatmap comparativo
pivot_cmp = df.groupby(['Implementador', 'Mes']).size().unstack(fill_value=0)

# Correlación Antigüedad vs Volumen
df['DiasDesde'] = (today - df['Fecha Llegada a Revisión']).dt.days
corr = df.groupby('Implementador').agg({'DiasDesde':'mean',}).reset_index()
corr['Tareas'] = df.groupby('Implementador').size().values

# Predicción de tareas futuros
def predecir_tareas(data):
    grp = data.groupby('Fecha Llegada a Revisión').size().reset_index(name='Tareas')
    grp['Día'] = (grp['Fecha Llegada a Revisión'] - grp['Fecha Llegada a Revisión'].min()).dt.days
    m, b = np.polyfit(grp['Día'], grp['Tareas'], 1)
    future_x = np.arange(grp['Día'].max(), grp['Día'].max() + 30)
    pred = m * future_x + b
    dates = grp['Fecha Llegada a Revisión'].min() + pd.to_timedelta(future_x, 'D')
    return pd.DataFrame({'Fecha': dates, 'Predicción': pred})

pred_df = predecir_tareas(df)

# --- Crear pestañas ---
tabs = st.tabs(["🏠 Resumen", "📊 Análisis General", "📈 Comparativas", "🔍 Correlación", "🔮 Predicción", "➕ Extras"])

# --- Resumen ---
with tabs[0]:
    st.header("🏠 Resumen General")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Tareas", len(df))
    c2.metric("Implementadores", df['Implementador'].nunique())
    prom = len(df)/df['Implementador'].nunique() if df['Implementador'].nunique() else 0
    c3.metric("Tareas/Impl (prom)", f"{prom:.1f}")
    st.divider()
    if st.checkbox("👁️ Mostrar vista previa de datos"):
        st.subheader("📋 Vista previa de Datos")
        st.dataframe(df, use_container_width=True)

# --- Análisis General ---
with tabs[1]:
    st.header("📊 Tareas por Implementador")
    st.markdown("Cada barra muestra la cantidad total de tareas asignadas a cada implementador.")
    fig1 = px.bar(cnt, x='Implementador', y='Tareas', text='Tareas', color='Tareas', color_continuous_scale='Blues')
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📆 Evolución Mensual de Tareas")
    st.markdown("La línea muestra la tendencia del número de tareas completadas mes a mes.")
    fig2 = px.line(mes, x='Mes', y='Tareas', markers=True)
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# --- Comparativas ---
with tabs[2]:
    st.header("📈 Comparativa Anual")
    st.markdown("Barras agrupadas que comparan el desempeño anual de cada implementador.")
    fig3 = px.bar(anual, x='Año', y='Tareas', color='Implementador', barmode='group')
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🌡️ Heatmap Mes vs Mes")
    st.markdown("Mapa de calor que muestra la intensidad de tareas por mes y por implementador.")
    fig4 = px.imshow(pivot_cmp, color_continuous_scale='Blues', labels={'color':'Tareas'})
    st.plotly_chart(fig4, use_container_width=True)

# --- Correlación ---
with tabs[3]:
    st.header("🔍 Correlación: Antigüedad vs Volumen")
    st.markdown("Cada punto representa un implementador; eje X es antigüedad media en días y eje Y es volumen de tareas.")
    fig5 = px.scatter(corr, x='DiasDesde', y='Tareas', text='Implementador')
    st.plotly_chart(fig5, use_container_width=True)

# --- Predicción ---
with tabs[4]:
    st.header("🔮 Predicción de Tareas (30 días)")
    st.markdown("Proyección lineal basada en los datos históricos de tareas para los próximos 30 días.")
    fig6 = px.line(pred_df, x='Fecha', y='Predicción', markers=True)
    st.plotly_chart(fig6, use_container_width=True)

# --- Extras ---
with tabs[5]:
    st.header("➕ Gráficas Avanzadas")
    # Radar Chart
    st.subheader("🔺 Radar Chart: Tareas vs Antigüedad")
    radar_df = corr.set_index('Implementador')[['Tareas', 'DiasDesde']]
    fig_radar = go.Figure()
    for imp in radar_df.index:
        fig_radar.add_trace(go.Scatterpolar(r=radar_df.loc[imp].values, theta=radar_df.columns, fill='toself', name=imp))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
    st.plotly_chart(fig_radar, use_container_width=True)

    # Boxplot
    st.subheader("📦 Boxplot de Tareas")
    st.markdown("Distribución de tareas por implementador, mostrando medianas y outliers.")
    fig_box, ax = plt.subplots(figsize=(8,4))
    sns.boxplot(x='Implementador', y='Tareas', data=cnt, ax=ax)
    plt.xticks(rotation=45)
    st.pyplot(fig_box)

    # Heatmap Semanal
    st.subheader("📅 Heatmap Semanal")
    df['Semana'] = df['Fecha Llegada a Revisión'].dt.isocalendar().week
    semanal = df.groupby(['Implementador', 'Semana']).size().unstack(fill_value=0)
    st.markdown("Mapa semanal de actividad para cada implementador.")
    fig_hm, ax = plt.subplots(figsize=(10,6))
    sns.heatmap(semanal, cmap='YlOrRd', ax=ax)
    plt.xlabel('Semana del Año')
    plt.ylabel('Implementador')
    st.pyplot(fig_hm)

    # Scatter Avanzado
    st.subheader("🔀 Scatter Avanzado")
    st.markdown("Tamaño de punto proporcional al volumen de tareas; color diferenciador por implementador.")
    fig_sc = px.scatter(corr, x='DiasDesde', y='Tareas', color='Implementador', size='Tareas', hover_name='Implementador')
    st.plotly_chart(fig_sc, use_container_width=True)
