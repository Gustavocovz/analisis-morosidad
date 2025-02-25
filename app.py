import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Configurar el título de la aplicación
st.title("📊 Análisis de Cohortes - Tasa de Morosidad (>30 días) basada en Saldo Real")

# Cargar el archivo Excel
file_path = "cosecha.xlsx"
df = pd.read_excel(file_path, sheet_name='vintage_analysis_report_2025022')

# Convertir fechas a formato datetime
df['disbursement_date'] = pd.to_datetime(df['disbursement_date'], errors='coerce')
df['last_date_of_month'] = pd.to_datetime(df['last_date_of_month'], errors='coerce')

# Crear columna de cohorte (primer préstamo del cliente)
df['cohort_month'] = df.groupby('vat')['disbursement_date'].transform('min').dt.to_period('M')
df['analysis_month'] = df['last_date_of_month'].dt.to_period('M')

# Indicar si el préstamo tiene más de 30 días de atraso
df['mora_30_dias'] = df['days_overdue'] > 30

# Calcular la diferencia en meses entre desembolso y análisis
df['cohort_index'] = (df['analysis_month'] - df['cohort_month']).apply(lambda x: x.n)

# Filtrar solo los valores donde cohort_index sea positivo o cero
df = df[df['cohort_index'] >= 0]

# Calcular el saldo actual de préstamos en mora (>30 días)
df['saldo_mora'] = df['mora_30_dias'] * df['aum']  # Solo los préstamos en mora suman su saldo actual

# Obtener los años disponibles sin duplicaciones
years = sorted(df['cohort_month'].dt.year.unique())

# Obtener los valores únicos de los filtros adicionales
filters = ['adviser', 'analyst', 'motive', 'evaluation_type', 'score_range',
           'worst_score', 'condition', 'guarantee_zone', 'guarantee_ownership',
           'age_range', 'dti_range', 'exceptions']

filter_values = {col: ['Todos'] + sorted(df[col].dropna().unique().astype(str)) for col in filters}

# Crear los selectores en la barra lateral
st.sidebar.header("📌 Filtros")
selected_year = st.sidebar.selectbox("Año:", years)
selected_month_range = st.sidebar.selectbox("Rango de Meses:",
                                            ["Meses 1-12", "Meses 13-24", "Meses 25-36", "Meses 37-48", "Meses 49-60"])

selected_filters = {col: st.sidebar.selectbox(col.replace('_', ' ').title(), options) for col, options in filter_values.items()}

# Aplicar filtros a los datos
def filter_data(df, filters, year):
    filtered_df = df[df['cohort_month'].dt.year == year]
    for col, value in filters.items():
        if value != "Todos":
            filtered_df = filtered_df[filtered_df[col].astype(str) == value]
    return filtered_df

# Filtrar los datos según los filtros seleccionados
df_filtered = filter_data(df, selected_filters, selected_year)

# Calcular la tabla de cohortes después del filtrado
total_saldo_cohorte = df_filtered.pivot_table(index='cohort_month', columns='cohort_index', values='debt_amount', aggfunc='sum')
saldo_mora_cohorte = df_filtered.pivot_table(index='cohort_month', columns='cohort_index', values='saldo_mora', aggfunc='sum')
cohort_mora_table = saldo_mora_cohorte.div(total_saldo_cohorte)
cohort_mora_table[cohort_mora_table == 0] = np.nan  # Reemplazar 0% por NaN para visualización limpia

# Definir los rangos de meses antes de usarlos
month_ranges = {
    "Meses 1-12": list(range(0, 12)),
    "Meses 13-24": list(range(12, 24)),
    "Meses 25-36": list(range(24, 36)),
    "Meses 37-48": list(range(36, 48)),
    "Meses 49-60": list(range(48, 60))
}

# Filtrar la tabla de cohortes según el año seleccionado
if str(selected_year) in cohort_mora_table.index:
    filtered_cohort_table = cohort_mora_table.loc[str(selected_year)]
else:
    filtered_cohort_table = None

# Obtener los meses a incluir
months_to_include = month_ranges[selected_month_range] if filtered_cohort_table is not None else []
months_to_include = [m for m in months_to_include if m in filtered_cohort_table.columns] if filtered_cohort_table is not None else []

# Graficar el heatmap si hay datos
if filtered_cohort_table is not None and months_to_include:
    plt.figure(figsize=(10, 5))
    sns.heatmap(filtered_cohort_table[months_to_include], annot=True, fmt=".1%", cmap="Reds", linewidths=0.5, mask=filtered_cohort_table[months_to_include].isna())
    plt.title(f"Tasa de Morosidad (>30 días) basada en Saldo - Año {selected_year}")
    plt.xlabel("Meses desde la Cohorte")
    plt.ylabel("Fecha de Cohorte")
    st.pyplot(plt)
else:
    st.warning("⚠️ No hay datos disponibles para esta combinación de filtros.")