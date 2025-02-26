import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de Streamlit
st.set_page_config(layout="wide", page_title="Análisis de Cohortes con Plotly")

# Función para cargar datos
@st.cache_data
def cargar_datos():
    file_path = "cosecha.xlsx"
    xls = pd.ExcelFile(file_path)
    df = pd.read_excel(xls, sheet_name='vintage_analysis_report_2025022')

    df['disbursement_date'] = pd.to_datetime(df['disbursement_date'], errors='coerce')
    df['last_date_of_month'] = pd.to_datetime(df['last_date_of_month'], errors='coerce')
    df['year_disbursement'] = df['disbursement_date'].dt.year.astype(str)  
    df['cohort_month'] = df['disbursement_date'].dt.to_period('M')  

    return df

df = cargar_datos()

# Sidebar: Filtros
st.sidebar.header("Filtros")
years = ["Todos"] + sorted(df["year_disbursement"].dropna().unique().tolist(), reverse=True)
selected_year = st.sidebar.selectbox("Año de desembolso", years, index=0)

dias_morosidad = st.sidebar.slider("Días de Atraso", min_value=30, max_value=120, step=30, value=30)

# Aplicar filtros
df_filtrado = df.copy()
if selected_year != "Todos":
    df_filtrado = df_filtrado[df_filtrado["year_disbursement"] == selected_year]

df_filtrado = df_filtrado[df_filtrado["days_overdue"] > dias_morosidad]

if df_filtrado.empty:
    st.warning("No hay datos para los filtros seleccionados")
    st.stop()

# Crear cohortes
df_filtrado["months_since_disbursement"] = (
    df_filtrado["last_date_of_month"].dt.to_period("M") - df_filtrado["disbursement_date"].dt.to_period("M")
).apply(lambda x: x.n)

cohort_morosidad = df_filtrado.pivot_table(
    index="cohort_month",
    columns="months_since_disbursement",
    values="aum",
    aggfunc="sum",
    fill_value=0
) / df_filtrado.groupby("cohort_month")["debt_amount"].sum().values[:, None]

# Generar Heatmap con Plotly
st.subheader(f"Análisis de Cohortes - Morosidad (> {dias_morosidad} días)")
fig = px.imshow(cohort_morosidad, 
                labels=dict(x="Meses Transcurridos", y="Cohorte", color="% Morosidad"),
                x=cohort_morosidad.columns,
                y=cohort_morosidad.index.astype(str),
                color_continuous_scale="Blues")

fig.update_layout(height=600, width=1000)

# Hacer clic en el heatmap y mostrar detalles
st.plotly_chart(fig)

st.sidebar.subheader("Ver detalles")
selected_cohort = st.sidebar.selectbox("Selecciona un cohorte", cohort_morosidad.index.astype(str))

if selected_cohort:
    st.write(f"Detalles para la cohorte {selected_cohort}:")
    df_detalles = df[(df["cohort_month"].astype(str) == selected_cohort) & (df["days_overdue"] > dias_morosidad)]
    st.dataframe(df_detalles)
