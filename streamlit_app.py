import streamlit as st
import pandas as pd

def assegna_fascia(data):
    giorno = data.weekday()
    ora = data.hour
    
    if giorno == 6: # Domenica
        return 'F3'
    elif giorno == 5: # Sabato
        if 7 <= ora < 23:
            return 'F2'
        else:
            return 'F3'
    else: # Lun-Ven
        if 8 <= ora < 19:
            return 'F1'
        elif (ora == 7) or (19 <= ora < 23):
            return 'F2'
        else:
            return 'F3'

st.title("Calcolatore Prezzi Fasce F1-F2-F3")

uploaded_file = st.file_uploader("Carica il file dati GME (CSV o Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Assicurati che le colonne siano corrette (Data e Prezzo)
    st.write("Anteprima dati:", df.head())
    
    col_data = st.selectbox("Seleziona la colonna Data", df.columns)
    col_prezzo = st.selectbox("Seleziona la colonna Prezzo (PUN)", df.columns)
    
    df[col_data] = pd.to_datetime(df[col_data])
    df['Fascia'] = df[col_data].apply(assegna_fascia)
    
    # Calcolo medie
    risultati = df.groupby('Fascia')[col_prezzo].mean().reset_index()
    risultati.columns = ['Fascia', 'Prezzo Medio (€/MWh)']
    
    # Conversione in €/kWh
    risultati['Prezzo Medio (€/kWh)'] = risultati['Prezzo Medio (€/MWh)'] / 1000
    
    st.header("Risultati per Fascia")
    st.table(risultati)
    
    st.bar_chart(data=risultati, x='Fascia', y='Prezzo Medio (€/MWh)')
