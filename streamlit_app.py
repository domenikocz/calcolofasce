import streamlit as st
import pandas as pd
import datetime

def get_festivita_italiane(anno):
    """Calcola le festività nazionali italiane per l'anno selezionato."""
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
    
    # Algoritmo di Butcher per la Pasqua
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
    mese_p = (h + l - 7 * m + 114) // 31
    giorno_p = ((h + l - 7 * m + 114) % 31) + 1
    pasquetta = datetime.date(anno, mese_p, giorno_p) + datetime.timedelta(days=1)
    festivita.append(pasquetta)
    return festivita

def assegna_fascia(row, festivita):
    data = row['Data_Completa']
    giorno_sett = data.weekday() 
    ora = data.hour
    
    # F3: Domeniche e Festivi
    if giorno_sett == 6 or data.date() in festivita:
        return 'F3'
    # Sabato
    if giorno_sett == 5:
        return 'F2' if 7 <= ora < 23 else 'F3'
    # Feriali
    if 8 <= ora < 19:
        return 'F1'
    elif ora == 7 or 19 <= ora < 23:
        return 'F2'
    else:
        return 'F3'

st.title("GME Excel Fasce Analyzer (2004-2026)")

# Sidebar per filtri
with st.sidebar:
    anno_sel = st.selectbox("Anno", list(range(2026, 2003, -1)))
    mese_sel = st.selectbox("Mese", list(range(1, 13)))

uploaded_file = st.file_uploader("Carica file Excel GME", type=['xlsx'])

if uploaded_file:
    try:
        # Legge il file Excel. Il GME solitamente ha i dati nel primo foglio.
        # Spesso i dati iniziano dopo alcune righe di disclaimer (es. skipfooter/header)
        df = pd.read_excel(uploaded_file)
        
        # Pulizia nomi colonne
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # Mapping colonne GME standard
        col_data = "Data/Date (YYYYMMDD)"
        col_ora = "Ora /Hour"
        col_pun = "PUN INDEX GME"

        if col_data in df.columns:
            # Conversione date e ore
            df['Data_Str'] = df[col_data].astype(str)
            df['Ora_Adj'] = df[col_ora].astype(int) - 1
            df['Data_Completa'] = pd.to_datetime(df['Data_Str'], format='%Y%m%d') + \
                                  pd.to_timedelta(df['Ora_Adj'], unit='h')

            # Filtro temporale
            mask = (df['Data_Completa'].dt.year == anno_sel) & (df['Data_Completa'].dt.month == mese_sel)
            df_mese = df.loc[mask].copy()

            if df_mese.empty:
                st.warning(f"Dati non trovati per {mese_sel}/{anno_sel}")
            else:
                festivita = get_festivita_italiane(anno_sel)
                df_mese['Fascia'] = df_mese.apply(lambda r: assegna_fascia(r, festivita), axis=1)

                # Calcolo Medie
                res = {
                    "F0 (PUN Medio)": df_mese[col_pun].mean(),
                    "F1": df_mese[df_mese['Fascia'] == 'F1'][col_pun].mean(),
                    "F2": df_mese[df_mese['Fascia'] == 'F2'][col_pun].mean(),
                    "F3": df_mese[df_mese['Fascia'] == 'F3'][col_pun].mean()
                }

                st.subheader(f"Analisi Prezzi {mese_sel}/{anno_sel}")
                
                # Visualizzazione in tabella
                final_df = pd.DataFrame(res.items(), columns=['Parametro', '€/MWh'])
                final_df['€/kWh'] = final_df['€/MWh'] / 1000
                st.table(final_df.style.format({'€/MWh': '{:.2f}', '€/kWh': '{:.5f}'}))
                
                st.line_chart(df_mese.set_index('Data_Completa')[col_pun])
        else:
            st.error("Formato colonne non riconosciuto. Verifica che il file sia un report prezzi GME.")

    except Exception as e:
        st.error(f"Errore: {e}")
