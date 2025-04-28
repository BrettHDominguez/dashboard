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

# --- Subida de Archivo ---
uploaded_file = st.sidebar.file_uploader("📂 Sube tu archivo Excel", type=["xlsx","xls"])
if not uploaded_file:
    st.info("↗️ Por favor, sube un archivo para comenzar")
    st.stop()

df = pd.read_excel(uploaded_file)
df.columns = df.columns.str.strip()
required_cols = ['Implementador', 'Fecha Llegada a Revisión']
if not all(col in df.columns for col in required_cols):
    st.error(f"❌ El archivo debe contener las columnas: {required_cols}")
    st.stop()

df['Fecha Llegada a Revisión'] = pd.to_datetime(df['Fecha Llegada a Revisión'], errors='coerce')
df.dropna(subset=['Fecha Llegada a Revisión'], inplace=True)

# --- Filtros en Sidebar ---
st.sidebar.header("🎛️ Filtros")
impls = sorted(df['Implementador'].unique())
sel_impl = st.sidebar.multiselect("Implementadores", impls, default=impls)
df = df[df['Implementador'].isin(sel_impl)]
fecha_min = df['Fecha Llegada a Revisión'].dt.date.min()
fecha_max = df['Fecha Llegada a Revisión'].dt.date.max()
fecha_inicio, fecha_fin = st.sidebar.slider(
    "Rango de fechas",
    min_value=fecha_min,
    max_value=fecha_max,
    value=(fecha_min, fecha_max),
    format="DD/MM/YYYY"
)
df = df[(df['Fecha Llegada a Revisión'].dt.date >= fecha_inicio) &
        (df['Fecha Llegada a Revisión'].dt.date <= fecha_fin)]

# --- Notificaciones en tiempo real ---
today = pd.Timestamp(datetime.now().date())
vencidas = df[df['Fecha Llegada a Revisión'] < today]
proximas = df[(df['Fecha Llegada a Revisión'] >= today) &
              (df['Fecha Llegada a Revisión'] <= today + pd.Timedelta(days=3))]
if not vencidas.empty:
    st.warning(f"⚠️ Tareas vencidas: {len(vencidas)}")
if not proximas.empty:
    st.info(f"⏰ Tareas próximas a vencer (3 días): {len(proximas)}")

# --- Predicción de Tareas ---
def predecir_tareas(df):
    grp = df.groupby('Fecha Llegada a Revisión').size().reset_index(name='Tareas')
    grp['Día'] = (grp['Fecha Llegada a Revisión'] - grp['Fecha Llegada a Revisión'].min()).dt.days
    m, b = np.polyfit(grp['Día'], grp['Tareas'], 1)
    future_x = np.arange(grp['Día'].max(), grp['Día'].max() + 30)
    pred = m * future_x + b
    dates = grp['Fecha Llegada a Revisión'].min() + pd.to_timedelta(future_x, 'D')
    return dates, pred

# --- Pestañas Principales ---
tabs = st.tabs(["🏠 Resumen", "📊 Análisis General", "📈 Comparativas", "🔍 Correlación", "🔮 Predicción", "➕ Extras"])

# --- Resumen ---
with tabs[0]:
    st.header("🏠 Resumen General")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Tareas", len(df))
    col2.metric("Implementadores", df['Implementador'].nunique())
    promedio = len(df) / df['Implementador'].nunique() if df['Implementador'].nunique() else 0
    col3.metric("Tareas/Impl (prom)", f"{promedio:.1f}")
    st.divider()
    st.subheader("📋 Vista previa de Datos")
    st.dataframe(df, use_container_width=True)

# --- Análisis General ---
with tabs[1]:
    st.header("📊 Tareas por Implementador")
    cnt = df['Implementador'].value_counts().reset_index()
    cnt.columns = ['Implementador', 'Tareas']
    st.markdown("**Cómo leer:** Cada barra muestra el total de tareas asignadas.")
    fig1 = px.bar(cnt, x='Implementador', y='Tareas', text='Tareas', color='Tareas', color_continuous_scale='Blues')
    fig1.update_layout(title="Volumen de Tareas por Implementador", xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📆 Evolución Mensual de Tareas")
    df['Mes'] = df['Fecha Llegada a Revisión'].dt.to_period('M').astype(str)
    mes = df.groupby('Mes').size().reset_index(name='Tareas')
    st.markdown("**Cómo leer:** La línea muestra cómo varía el número de tareas mes a mes.")
    fig2 = px.line(mes, x='Mes', y='Tareas', markers=True)
    fig2.update_layout(title="Tendencia Mensual", xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# --- Comparativas ---
with tabs[2]:
    st.header("📈 Comparativas Anuales")
    df['Año'] = df['Fecha Llegada a Revisión'].dt.year
    anual = df.groupby(['Año', 'Implementador']).size().reset_index(name='Tareas')
    st.markdown("**Cómo leer:** Barras agrupadas comparan desempeño anual por implementador.")
    fig3 = px.bar(anual, x='Año', y='Tareas', color='Implementador', barmode='group')
    fig3.update_layout(title="Comparativa Anual")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🌡️ Heatmap Mes vs Mes")
    pivot = df.pivot_table(index='Implementador', columns='Mes', values='Fecha Llegada a Revisión', aggfunc='count', fill_value=0)
    st.markdown("**Cómo leer:** El color refleja la cantidad de tareas por mes e implementador.")
    fig4 = px.imshow(pivot, color_continuous_scale='Blues', labels={'color':'Tareas'})
    st.plotly_chart(fig4, use_container_width=True)

# --- Correlación ---
with tabs[3]:
    st.header("🔍 Correlación: Antigüedad vs Volumen")
    df['DiasDesde'] = (today - df['Fecha Llegada a Revisión']).dt.days
    corr = df.groupby('Implementador')['DiasDesde'].mean().reset_index()
    corr['Tareas'] = df.groupby('Implementador').size().values
    st.markdown("**Cómo leer:** Cada punto representa un implementador; su posición indica antigüedad y volumen.")
    fig5 = px.scatter(corr, x='DiasDesde', y='Tareas', text='Implementador')
    fig5.update_layout(title="Scatter Antigüedad vs Volumen")
    st.plotly_chart(fig5, use_container_width=True)

# --- Predicción ---
with tabs[4]:
    st.header("🔮 Predicción de Tareas (30 días)")
    dates, pred = predecir_tareas(df)
    pred_df = pd.DataFrame({'Fecha': dates, 'Predicción': pred})
    st.markdown("**Cómo leer:** Proyección de tareas para los próximos 30 días basada en tendencia histórica.")
    fig6 = px.line(pred_df, x='Fecha', y='Predicción', markers=True)
    fig6.update_layout(title="Forecast 30 Días", xaxis_tickangle=-45)
    st.plotly_chart(fig6, use_container_width=True)

# --- Extras ---
with tabs[5]:
    st.header("➕ Gráficas Avanzadas")
    
    # Radar Chart
    st.subheader("🔺 Radar Chart: Tareas vs Antigüedad")
    st.markdown("**Cómo leer:** Compara volumen y antigüedad media en un gráfico polar.")
    metrics = ['Tareas', 'DiasDesde']
    radar_df = pd.DataFrame({imp: [cnt.set_index('Implementador').at[imp,'Tareas'], corr.set_index('Implementador').at[imp,'DiasDesde']] for imp in cnt['Implementador']}, index=metrics).T
    fig_radar = go.Figure()
    for imp in radar_df.index:
        fig_radar.add_trace(go.Scatterpolar(r=radar_df.loc[imp].values, theta=metrics, fill='toself', name=imp))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # Boxplot
    st.subheader("📦 Boxplot de Tareas")
    st.markdown("**Cómo leer:** La caja muestra mediana, cuartiles y posibles outliers.")
    fig_box, ax = plt.subplots(figsize=(8,4))
    sns.boxplot(x='Implementador', y='Tareas', data=cnt, ax=ax)
    plt.xticks(rotation=45)
    st.pyplot(fig_box)
    
    # Heatmap Semanal
    st.subheader("📅 Heatmap Semanal")
    st.markdown("**Cómo leer:** Semanas del año vs tareas por implementador.")
    semanal = df.pivot_table(index='Implementador', columns=df['Fecha Llegada a Revisión'].dt.isocalendar().week, values='Fecha Llegada a Revisión', aggfunc='count', fill_value=0)
    fig_hm, ax = plt.subplots(figsize=(10,6))
    sns.heatmap(semanal, cmap='YlOrRd', ax=ax)
    plt.xlabel('Semana del Año')
    plt.ylabel('Implementador')
    st.pyplot(fig_hm)
    
    # Scatter Avanzado
    st.subheader("🔀 Scatter Avanzado")
    st.markdown("**Cómo leer:** Tamaño de punto proporcional al volumen de tareas.")
    fig_sc = px.scatter(corr, x='DiasDesde', y='Tareas', color='Implementador', size='Tareas', hover_name='Implementador')
    fig_sc.update_layout(title="Scatter Avanzado")
    st.plotly_chart(fig_sc, use_container_width=True)
