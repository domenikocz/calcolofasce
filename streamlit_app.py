import streamlit as st
import pandas as pd
import datetime
import os
import glob

def get_festivita_italiane(anno):
    festivita = [
        datetime.date(anno, 1, 1), datetime.date(anno, 1, 6),
        datetime.date(anno, 4, 25), datetime.date(anno, 5, 1),
        datetime.date(anno, 6, 2), datetime.date(anno, 8, 15),
        datetime.date(anno, 11, 1), datetime.date(anno, 12, 8),
        datetime.date(anno, 12, 25), datetime.date(anno, 12, 26),
    ]
    # Pasquetta
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese_p = (h + l - 7 * m + 114) // 31
    giorno_p = ((h + l - 7 * m + 114) % 31) + 1
    festivita.append(datetime.date(anno, mese_p, giorno_p) + datetime.timedelta(days=1))
    return festivita

def assegna_fascia(row, festivita):
    ora = int(row['Ora_Pulita']) - 1
    data_obj = row['Data_DT'].date()
    giorno_sett = data_obj.weekday()
    if giorno_sett == 6 or data_obj in festivita:
        return 'F3'
    if giorno_sett == 5:
        return 'F2' if 7 <= ora < 23 else 'F3'
    return 'F1' if 8 <= ora < 19 else ('F2' if (ora == 7 or 19 <= ora < 23) else 'F3')

@st.cache_data
def load_data_auto(anno):
    # Cerca qualsiasi file che inizi con "Anno [anno]"
    pattern = f"Anno {anno}*.xlsx*"
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Prende il primo file trovato
    filepath = files[0]
    
    # Gestione CSV o Excel
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)
    
    # Pulizia nomi colonne
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    return df

st.set_page_config(page_title="GME Multi-Year Analyzer", layout="wide")
st.title("Analizzatore PUN da Repository")

with st.sidebar:
    anno_sel = st.selectbox("Anno", list(range(2026, 2003, -1)))
    mese_sel = st.selectbox("Mese", list(range(1, 13)))

df_raw = load_data_auto(anno_sel)

if df_raw is not None:
    try:
        # Trova le colonne corrette (possono cambiare tra gli anni)
        col_data = next((c for c in df_raw.columns if 'Data' in c or 'Date' in c), None)
        col_ora = next((c for c in df_raw.columns if 'Ora' in c or 'Hour' in c), None)
        # Il PUN può chiamarsi "PUN" o "PUN INDEX GME"
        col_pun = next((c for c in df_raw.columns if 'PUN' in c), None)

        if not all([col_data, col_ora, col_pun]):
            st.error(f"Colonne non trovate. Disponibili: {list(df_raw.columns)}")
        else:
            df_raw['Data_DT'] = pd.to_datetime(df_raw[col_data].astype(str), format='%Y%m%d', errors='coerce')
            df_mese = df_raw[df_raw['Data_DT'].dt.month == mese_sel].copy()

            if df_mese.empty:
                st.warning(f"Nessun dato per {mese_sel}/{anno_sel}")
            else:
                df_mese['Ora_Pulita'] = df_mese[col_ora].astype(int)
                festivita = get_festivita_italiane(anno_sel)
                df_mese['Fascia'] = df_mese.apply(lambda r: assegna_fascia(r, festivita), axis=1)

                # Calcolo Medie (gestendo i 15 min o orari)
                # Se ci sono più righe per la stessa ora (quarti d'ora), facciamo la media oraria
                df_orario = df_mese.groupby(['Data_DT', 'Ora_Pulita', 'Fascia'])[col_pun].mean().reset_index()

                f1 = df_orario[df_orario['Fascia'] == 'F1'][col_pun].mean()
                f2 = df_orario[df_orario['Fascia'] == 'F2'][col_pun].mean()
                f3 = df_orario[df_orario['Fascia'] == 'F3'][col_pun].mean()
                f0 = df_orario[col_pun].mean()

                st.subheader(f"Riepilogo {mese_sel}/{anno_sel}")
                res_df = pd.DataFrame({
                    "Fascia": ["F0 (PUN)", "F1", "F2", "F3"],
                    "€/MWh": [f0, f1, f2, f3],
                    "€/kWh": [f0/1000, f1/1000, f2/1000, f3/1000]
                })
                st.table(res_df.style.format({'€/MWh': '{:.4f}', '€/kWh': '{:.6f}'}))
                
                st.subheader("Dettaglio PUN Orario")
                st.line_chart(df_orario.set_index('Data_DT')[col_pun])
                st.dataframe(df_orario)

    except Exception as e:
        st.error(f"Errore: {e}")
else:
    st.error(f"File per l'anno {anno_sel} non trovato nel repository (es. Anno {anno_sel}_12.xlsx)")
