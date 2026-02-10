import streamlit as st
import pandas as pd
import datetime

def get_festivita_italiane(anno):
    """Restituisce le date delle festività nazionali italiane per un dato anno."""
    festivita = [
        datetime.date(anno, 1, 1),   # Capodanno
        datetime.date(anno, 1, 6),   # Epifania
        datetime.date(anno, 4, 25),  # Liberazione
        datetime.date(anno, 5, 1),   # Lavoro
        datetime.date(anno, 6, 2),   # Repubblica
        datetime.date(anno, 8, 15),  # Ferragosto
        datetime.date(anno, 11, 1),  # Ognissanti
        datetime.date(anno, 12, 8),  # Immacolata
        datetime.date(anno, 12, 25), # Natale
        datetime.date(anno, 12, 26), # S. Stefano
    ]
    
    # Calcolo Pasquetta (Lunedì dell'Angelo)
    a = anno % 19
    b = anno // 100
    c = anno % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese_pasqua = (h + l - 7 * m + 114) // 31
    giorno_pasqua = ((h + l - 7 * m + 114) % 31) + 1
    
    pasqua = datetime.date(anno, mese_pasqua, giorno_pasqua)
    pasquetta = pasqua + datetime.timedelta(days=1)
    festivita.append(pasquetta)
    
    return festivita

def assegna_fascia(row, festivita):
    data = row['Data_Completa']
    giorno_sett = data.weekday() # 0=Lun, 6=Dom
    ora = data.hour
    data_solo_giorno = data.date()

    # F3: Domeniche e Festività Nazionali
    if giorno_sett == 6 or data_solo_giorno in festivita:
        return 'F3'
    
    # Sabato
    if giorno_sett == 5:
        if 7 <= ora < 23:
            return 'F2'
        else:
            return 'F3'
    
    # Lunedì - Venerdì
    if 8 <= ora < 19:
        return 'F1'
    elif (ora == 7) or (19 <= ora < 23):
        return 'F2'
    else:
        return 'F3'

# Configurazione Streamlit
st.set_page_config(page_title="GME Fasce Analyzer", layout="wide")
st.title("Analizzatore Prezzi GME (2004-2026)")
st.write("Carica il file scaricato dal GME per calcolare le medie F0, F1, F2, F3.")

# Selezione Anno e Mese
col1, col2 = st.columns(2)
with col1:
    anno_sel = st.selectbox("Seleziona Anno", list(range(2026, 2003, -1)))
with col2:
    mese_sel = st.selectbox("Seleziona Mese", list(range(1, 13)))

uploaded_file = st.file_uploader("Carica il file CSV del GME", type=['csv'])

if uploaded_file:
    # Lettura file (salta header se necessario o gestisce nomi colonne)
    df = pd.read_csv(uploaded_file)
    
    # Pulizia nomi colonne (spesso hanno spazi o ritorni a capo nel CSV GME)
    df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
    
    col_data = "Data/Date (YYYYMMDD)"
    col_ora = "Ora /Hour"
    col_pun = "PUN INDEX GME"

    try:
        # Prepara la colonna datetime
        df['Data_Str'] = df[col_data].astype(str)
        # Sottrai 1 all'ora perché GME usa 1-24, Python usa 0-23
        df['Ora_Adj'] = df[col_ora].astype(int) - 1
        
        df['Data_Completa'] = pd.to_datetime(df['Data_Str'], format='%Y%m%d') + \
                              pd.to_timedelta(df['Ora_Adj'], unit='h')

        # Filtro per Anno e Mese selezionati
        df = df[(df['Data_Completa'].dt.year == anno_sel) & (df['Data_Completa'].dt.month == mese_sel)]

        if df.empty:
            st.warning(f"Nessun dato trovato per {mese_sel}/{anno_sel} nel file caricato.")
        else:
            # Calcolo fasce
            festivita = get_festivita_italiane(anno_sel)
            df['Fascia'] = df.apply(lambda r: assegna_fascia(r, festivita), axis=1)

            # Calcolo medie
            f1 = df[df['Fascia'] == 'F1'][col_pun].mean()
            f2 = df[df['Fascia'] == 'F2'][col_pun].mean()
            f3 = df[df['Fascia'] == 'F3'][col_pun].mean()
            f0 = df[col_pun].mean() # Media totale

            # Display Risultati
            st.header(f"Risultati {mese_sel}/{anno_sel}")
            
            res_cols = st.columns(4)
            res_cols[0].metric("F0 (Media Totale)", f"{f0:.5f} €/MWh")
            res_cols[1].metric("F1", f"{f1:.5f} €/MWh")
            res_cols[2].metric("F2", f"{f2:.5f} €/MWh")
            res_cols[3].metric("F3", f"{f3:.5f} €/MWh")

            # Tabella di dettaglio
            st.subheader("Dettaglio €/kWh")
            dati_kwh = {
                "Fascia": ["F0 (PUN)", "F1", "F2", "F3"],
                "Prezzo [€/kWh]": [f0/1000, f1/1000, f2/1000, f3/1000]
            }
            st.table(pd.DataFrame(dati_kwh))

    except Exception as e:
        st.error(f"Errore nella lettura del file: {e}. Assicurati che il formato sia quello standard del GME.")
