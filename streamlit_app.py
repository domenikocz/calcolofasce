import streamlit as st
import pandas as pd
import datetime
import os

def get_festivita_italiane(anno):
    """Calcola le festività nazionali italiane."""
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
    # L'ora nel file GME è 1-24. Python datetime usa 0-23.
    ora_zero_based = int(row['Ora']) - 1
    data_obj = row['Data_Obj']
    giorno_sett = data_obj.weekday() # 0=Lun, 6=Dom

    if giorno_sett == 6 or data_obj in festivita:
        return 'F3'
    if giorno_sett == 5:
        return 'F2' if 7 <= ora_zero_based < 23 else 'F3'
    if 8 <= ora_zero_based < 19:
        return 'F1'
    elif ora_zero_based == 7 or 19 <= ora_zero_based < 23:
        return 'F2'
    else:
        return 'F3'

@st.cache_data
def load_data_from_repo(anno):
    """Carica il file Excel dal repository in base all'anno."""
    # Gestione nomi file: i file dal 2025 hanno granularità 15 min
    if anno >= 2025:
        filename = f"Anno {anno}_12_15.xlsx"
    else:
        filename = f"Anno {anno}_12.xlsx" # Formato orario standard
    
    if os.path.exists(filename):
        df = pd.read_excel(filename)
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        return df
    return None

st.set_page_config(page_title="GME Fasce Analyzer", layout="wide")
st.title("Analizzatore Storico GME (2004-2026)")

# Sidebar per filtri
with st.sidebar:
    st.header("Seleziona Periodo")
    anno_sel = st.selectbox("Anno", list(range(2026, 2003, -1)))
    mese_sel = st.selectbox("Mese", list(range(1, 13)))
    st.info("I file vengono letti direttamente dalla cartella del repository.")

# Caricamento automatico
df_raw = load_data_from_repo(anno_sel)

if df_raw is not None:
    try:
        col_data = "Data/Date (YYYYMMDD)"
        col_ora = "Ora /Hour"
        col_pun = "PUN INDEX GME"

        # Trasformazione date e filtri
        df_raw['Data_DT'] = pd.to_datetime(df_raw[col_data].astype(str), format='%Y%m%d')
        df_mese = df_raw[df_raw['Data_DT'].dt.month == mese_sel].copy()

        if df_mese.empty:
            st.warning(f"Nessun dato trovato per {mese_sel}/{anno_sel}")
        else:
            df_mese['Data_Obj'] = df_mese['Data_DT'].dt.date
            df_mese['Ora'] = df_mese[col_ora]
            
            festivita = get_festivita_italiane(anno_sel)
            df_mese['Fascia'] = df_mese.apply(lambda r: assegna_fascia(r, festivita), axis=1)

            # Calcolo Medie
            f1 = df_mese[df_mese['Fascia'] == 'F1'][col_pun].mean()
            f2 = df_mese[df_mese['Fascia'] == 'F2'][col_pun].mean()
            f3 = df_mese[df_mese['Fascia'] == 'F3'][col_pun].mean()
            f0 = df_mese[col_pun].mean()

            st.header(f"Riepilogo {mese_sel}/{anno_sel}")
            
            # Tabella Risultati
            res_df = pd.DataFrame({
                "Parametro": ["F0 (PUN Medio)", "F1", "F2", "F3"],
                "€/MWh": [f0, f1, f2, f3],
                "€/kWh": [f0/1000, f1/1000, f2/1000, f3/1000]
            })
            st.table(res_df.style.format({'€/MWh': '{:.2f}', '€/kWh': '{:.5f}'}))

            # Dettaglio PUN Orario
            st.subheader("Andamento PUN Orario")
            # Per i file a 15 min, aggreghiamo per avere il valore orario
            pun_orario = df_mese.groupby([col_data, 'Ora', 'Fascia'])[col_pun].mean().reset_index()
            pun_orario.columns = ['Data', 'Ora', 'Fascia', 'PUN_Orario_MWh']
            
            st.line_chart(pun_orario.set_index('Ora')['PUN_Orario_MWh'])
            st.dataframe(pun_orario, use_container_width=True)

    except Exception as e:
        st.error(f"Errore nell'elaborazione dei dati: {e}")
else:
    st.error(f"File non trovato nel repository per l'anno {anno_sel}. Verificare la presenza del file Excel.")
