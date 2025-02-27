import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def cargar_datos():
    """
    Carga los datos desde el archivo 'cosecha.xlsx' sin eliminar valores nulos.
    """
    file_path = "cosecha.xlsx"
    xls = pd.ExcelFile(file_path)
    df = pd.read_excel(xls, sheet_name='vintage_analysis_report_2025022')
   
    # Convertir columnas de fecha
    df['disbursement_date'] = pd.to_datetime(df['disbursement_date'], errors='coerce')
    df['last_date_of_month'] = pd.to_datetime(df['last_date_of_month'], errors='coerce')
    
    # Eliminar registros con fecha de desembolso nula
    df = df.dropna(subset=['disbursement_date'])
    
    # Convertir año a entero
    df['year_disbursement'] = df['disbursement_date'].dt.year.astype(int)
    df['cohort_month'] = df['disbursement_date'].dt.to_period('M')
   
    return df

def generar_cohortes_morosidad(df, filtros=None, dias_morosidad=30):
    df_filtrado = df.copy()
   
    if filtros:
        for columna, valores in filtros.items():
            if valores:
                df_filtrado = df_filtrado[df_filtrado[columna].isin(valores)]
   
    if df_filtrado.empty:
        return None, None
   
    total_desembolsado = df_filtrado.groupby('cohort_month', as_index=False).agg(
        nro_desembolsado=('debt_amount', 'count'),
        total_desembolsado=('debt_amount', 'sum')
    )
   
    df_filtrado = df_filtrado[df_filtrado['days_overdue'] > dias_morosidad]
   
    if df_filtrado.empty:
        return None, None
   
    df_filtrado['morosidad_monto'] = df_filtrado['aum']
   
    df_filtrado = df_filtrado.dropna(subset=['disbursement_date', 'last_date_of_month'])
    df_filtrado['months_since_disbursement'] = (
        df_filtrado['last_date_of_month'].dt.to_period('M') - df_filtrado['disbursement_date'].dt.to_period('M')
    ).apply(lambda x: x.n if pd.notna(x) else 0)
   
    morosidad_agrupada = df_filtrado.groupby(['cohort_month', 'months_since_disbursement'], as_index=False).agg(
        nro_morosidad=('morosidad_monto', 'count'),
        total_morosidad=('morosidad_monto', 'sum')
    )
   
    morosidad_agrupada = morosidad_agrupada.merge(total_desembolsado, on='cohort_month', how='left')
   
    morosidad_agrupada['%_morosidad'] = morosidad_agrupada['total_morosidad'] / morosidad_agrupada['total_desembolsado']
   
    cohort_morosidad = morosidad_agrupada.pivot(
        index='cohort_month',
        columns='months_since_disbursement',
        values='%_morosidad'
    )
   
    cohort_morosidad = cohort_morosidad.where(cohort_morosidad > 0, other=None)
   
    return cohort_morosidad, morosidad_agrupada

def generar_heatmap(cohort_data, dias_morosidad):
    if cohort_data is None or cohort_data.empty:
        st.write("No se encontraron resultados con los filtros seleccionados.")
        return
   
    plt.figure(figsize=(14, 7))
    sns.heatmap(cohort_data, annot=True, fmt=".1%", cmap="Blues", linewidths=0.5, mask=cohort_data.isnull(), annot_kws={"size": 8})
    plt.title(f"Análisis de Cohortes - Morosidad (> {dias_morosidad} días) basada en Monto", loc='center', fontsize=12)
    plt.xlabel("Meses Transcurridos desde el Desembolso")
    plt.ylabel("Cohorte (Mes de Desembolso)")
    plt.yticks(rotation=0)  # Mantener los meses en horizontal
    st.pyplot(plt)

def mostrar_tabla(morosidad_agrupada):
    if morosidad_agrupada is None or morosidad_agrupada.empty:
        st.write("No hay datos disponibles para la tabla.")
        return
   
    st.write("### Datos de Morosidad Filtrados")
    st.dataframe(morosidad_agrupada)
   
    # Botón para exportar a CSV
    csv = morosidad_agrupada.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar CSV", data=csv, file_name="morosidad_filtrada.csv", mime="text/csv")

def main():
    st.set_page_config(layout="wide")  # Ajustar la barra lateral para más espacio en la visualización
    st.markdown("<h1 style='text-align: center;'>Análisis de Cohortes - Morosidad</h1>", unsafe_allow_html=True)
    df = cargar_datos()
   
    st.sidebar.header("Filtros")
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            min-width: 220px;
            max-width: 250px;
        }
        </style>
    """, unsafe_allow_html=True)
   
    dias_morosidad = st.sidebar.slider("Días de Atraso", min_value=30, max_value=120, step=30, value=30)
   
    columnas_filtrables = ['year_disbursement', 'adviser', 'analyst', 'motive', 'evaluation_type', 'score_range',
                           'worst_score', 'condition', 'guarantee_zone', 'guarantee_ownership',
                           'age_range', 'dti_range', 'exceptions']
   
    filtros_seleccionados = {}
    for col in columnas_filtrables:
        opciones = sorted(df[col].dropna().unique().tolist())
        seleccion = st.sidebar.multiselect(f"{col.replace('_', ' ').capitalize()}", opciones, key=col, 
                                           format_func=lambda x: str(x))
        if seleccion:
            filtros_seleccionados[col] = seleccion
   
    cohort_data, morosidad_agrupada = generar_cohortes_morosidad(df, filtros_seleccionados, dias_morosidad)
    generar_heatmap(cohort_data, dias_morosidad)
    mostrar_tabla(morosidad_agrupada)

if __name__ == "__main__":
    main()

