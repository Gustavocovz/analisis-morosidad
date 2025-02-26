import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

@st.cache_data
def cargar_datos():
    """
    Carga los datos desde el archivo 'cosecha.xlsx' sin eliminar valores nulos.
    """
    file_path = "cosecha.xlsx"
    xls = pd.ExcelFile(file_path)
    df = pd.read_excel(xls, sheet_name='vintage_analysis_report_2025022')
    
    df['disbursement_date'] = pd.to_datetime(df['disbursement_date'], errors='coerce')
    df['last_date_of_month'] = pd.to_datetime(df['last_date_of_month'], errors='coerce')
    df['year_disbursement'] = df['disbursement_date'].dt.year.astype(str)
    df['cohort_month'] = df['disbursement_date'].dt.to_period('M')
    
    return df

def generar_cohortes_morosidad(df, filtros=None, dias_morosidad=30):
    """
    Genera una tabla de cohortes de morosidad basada en monto en mora (>X días) sobre el monto total desembolsado.
    """
    df_filtrado = df.copy()
    
    if filtros:
        for columna, valores in filtros.items():
            if valores and "Todos" not in valores:
                df_filtrado = df_filtrado[df_filtrado[columna].isin(valores)]
    
    if df_filtrado.empty:
        return None
    
    total_desembolsado = df_filtrado.groupby('cohort_month', as_index=False)['debt_amount'].sum()
    
    df_filtrado = df_filtrado[df_filtrado['days_overdue'] > dias_morosidad]
    
    if df_filtrado.empty:
        return None
    
    df_filtrado['morosidad_monto'] = df_filtrado['aum']
    
    df_filtrado['months_since_disbursement'] = (
        df_filtrado['last_date_of_month'].dt.to_period('M') - df_filtrado['disbursement_date'].dt.to_period('M')
    ).apply(lambda x: x.n)
    
    morosidad_agrupada = df_filtrado.groupby(['cohort_month', 'months_since_disbursement'], as_index=False).agg(
        total_morosidad=('morosidad_monto', 'sum')
    )
    
    morosidad_agrupada = morosidad_agrupada.merge(total_desembolsado, on='cohort_month', how='left')
    morosidad_agrupada['morosidad_ratio'] = morosidad_agrupada['total_morosidad'] / morosidad_agrupada['debt_amount']
    
    cohort_morosidad = morosidad_agrupada.pivot(
        index='cohort_month',
        columns='months_since_disbursement',
        values='morosidad_ratio'
    )
    
    return cohort_morosidad

def generar_heatmap(cohort_data, dias_morosidad):
    """
    Genera un heatmap de la tabla de cohortes de morosidad.
    """
    plt.figure(figsize=(14, 7))
    sns.heatmap(cohort_data, annot=True, fmt=".1%", cmap="Blues", linewidths=0.5, mask=cohort_data.isnull(), annot_kws={"size": 8})
    plt.title(f"Análisis de Cohortes - Morosidad (> {dias_morosidad} días) basada en Monto")
    plt.xlabel("Meses Transcurridos desde el Desembolso")
    plt.ylabel("Cohorte (Mes de Desembolso)")
    plt.yticks(rotation=0)
    plt.xticks(rotation=0)
    st.pyplot(plt)

def main():
    st.title("Análisis de Cohortes - Morosidad")
    df = cargar_datos()
    
    columnas_filtrables = ['adviser', 'analyst', 'motive', 'evaluation_type', 'score_range',
                           'worst_score', 'condition', 'guarantee_zone', 'guarantee_ownership',
                           'age_range', 'dti_range', 'exceptions', 'year_disbursement']
    
    filtros = {}
    with st.sidebar:
        st.header("Filtros")
        for col in columnas_filtrables:
            valores = ['Todos'] + sorted(df[col].dropna().unique().tolist())
            seleccion = st.multiselect(f"{col}", valores, default=['Todos'])
            filtros[col] = seleccion
        
        dias_morosidad = st.slider("Días de Atraso", 30, 120, 30, step=30)
    
    cohort_data = generar_cohortes_morosidad(df, filtros, dias_morosidad)
    
    if cohort_data is not None:
        generar_heatmap(cohort_data, dias_morosidad)
    else:
        st.warning("No se encontraron resultados con los filtros seleccionados.")

if __name__ == "__main__":
    main()
