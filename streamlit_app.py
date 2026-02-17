import streamlit as st
import pandas as pd
import datetime
import glob

def get_festivita_italiane(anno):
    festivita = [datetime.date(anno, 1, 1), datetime.date(anno, 1, 6), datetime.date(anno, 4, 25), datetime.date(anno, 5, 1), datetime.date(anno, 6, 2), datetime.date(anno, 8, 15), datetime.date(anno, 11, 1), datetime.date(anno, 12, 8), datetime.date(anno, 12, 25), datetime.date(anno, 12, 26)]
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
    if 'Ora_Pulita' in row:
        ora, data_obj = int(row['Ora_Pulita']) - 1, row['Data_DT'].date()
    else:
        ora, data_obj = row['Datetime'].hour, row['Datetime'].date()
    giorno_sett = data_obj.weekday()
    if giorno_sett == 6 or data_obj in festivita: return 'F3'
    if giorno_sett == 5: return 'F2' if 7 <= ora < 23 else 'F3'
    return 'F1' if 8 <= ora < 19 else ('F2' if (ora == 7 or 19 <= ora < 23) else 'F3')

@st.cache_data
def load_data_auto(anno):
    pattern = f"Anno {anno}*.xlsx*"
    files = glob.glob(pattern)
    if not files: return None
    filepath = files[0]
    df = pd.read_csv(filepath, sep=None, engine='python', on_bad_lines='skip') if filepath.endswith('.csv') else pd.read_excel(filepath)
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    return df

st.set_page_config(page_title="GME Multi-Year Analyzer", layout="wide")
st.title("Calcolo Spesa Energetica")
st.subheader("1. Carica Curva di Carico (15 min)")
uploaded_file = st.file_uploader("Carica file curve", type=['xlsx', 'csv'])
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df_carico = pd.read_csv(uploaded_file, sep=';', decimal=',', engine='python', on_bad_lines='skip')
        else: df_carico = pd.read_excel(uploaded_file)
        if 'Giorno' in df_carico.columns and any('-' in str(c) for c in df_carico.columns):
            id_vars = ['Giorno']
            value_vars = [c for c in df_carico.columns if '-' in str(c)]
            df_melted = df_carico.melt(id_vars=id_vars, value_vars=value_vars, var_name='Intervallo', value_name='kWh')
            df_melted['Giorno'] = df_melted['Giorno'].astype(str)
            df_melted['Ora_Inizio'] = df_melted['Intervallo'].str.split('-').str[0].astype(str)
            df_melted['Datetime'] = pd.to_datetime(df_melted['Giorno'] + ' ' + df_melted['Ora_Inizio'], dayfirst=True, errors='coerce')
            df_melted['kWh'] = pd.to_numeric(df_melted['kWh'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df_carico, col_dt, col_kwh = df_melted, 'Datetime', 'kWh'
        else:
            col_dt = next((c for c in df_carico.columns if any(x in str(c) for x in ['Data', 'Time', 'Date'])), None)
            col_kwh = next((c for c in df_carico.columns if any(x in str(c) for x in ['Consum', 'kWh', 'Valore'])), None)
            if col_dt: df_carico['Datetime'] = pd.to_datetime(df_carico[col_dt], dayfirst=True, errors='coerce')
            if col_kwh: df_carico[col_kwh] = pd.to_numeric(df_carico[col_kwh].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        if not col_dt or not col_kwh: st.error("Formato non riconosciuto")
        else:
            df_carico = df_carico.dropna(subset=['Datetime'])
            anno_curva, mese_curva = df_carico['Datetime'].dt.year.iloc[0], df_carico['Datetime'].dt.month.iloc[0]
            st.info(f"Periodo: {mese_curva}/{anno_curva}")
            df_raw = load_data_auto(anno_curva)
            if df_raw is not None:
                c_data = next((c for c in df_raw.columns if 'Data' in c or 'Date' in c), None)
                c_ora = next((c for c in df_raw.columns if 'Ora' in c or 'Hour' in c), None)
                c_pun = next((c for c in df_raw.columns if 'PUN' in c), None)
                df_raw['Data_DT'] = pd.to_datetime(df_raw[c_data].astype(str), format='%Y%m%d', errors='coerce')
                df_pun_m = df_raw[df_raw['Data_DT'].dt.month == mese_curva].copy()
                df_pun_m['Ora_Pulita'] = df_pun_m[c_ora].astype(int)
                df_pun_m[c_pun] = pd.to_numeric(df_pun_m[c_pun].astype(str).str.replace(',', '.'), errors='coerce')
                fest = get_festivita_italiane(anno_curva)
                df_pun_m['Fascia'] = df_pun_m.apply(lambda r: assegna_fascia(r, fest), axis=1)
                f1_p, f2_p, f3_p, f0_p = df_pun_m[df_pun_m['Fascia']=='F1'][c_pun].mean()/1000, df_pun_m[df_pun_m['Fascia']=='F2'][c_pun].mean()/1000, df_pun_m[df_pun_m['Fascia']=='F3'][c_pun].mean()/1000, df_pun_m[c_pun].mean()/1000
                df_carico['Fascia'] = df_carico.apply(lambda r: assegna_fascia(r, fest), axis=1)
                c_tot, c1, c2, c3 = df_carico[col_kwh].sum(), df_carico[df_carico['Fascia']=='F1'][col_kwh].sum(), df_carico[df_carico['Fascia']=='F2'][col_kwh].sum(), df_carico[df_carico['Fascia']=='F3'][col_kwh].sum()
                st.markdown("---")
                st.subheader("Riquadro 1: Monoraria (F0)")
                s_f0 = c_tot * f0_p
                r1, r2, r3 = st.columns(3)
                r1.metric("Energia Totale (kWh)", f"{c_tot:,.2f}")
                r2.metric("PUN F0 (€/kWh)", f"{f0_p:.6f}")
                r3.metric("Totale Spesa F0", f"€ {s_f0:,.2f}")
                st.markdown("---")
                st.subheader("Riquadro 2: Fasce (F1, F2, F3)")
                s1, s2, s3 = c1*f1_p, c2*f2_p, c3*f3_p
                res = pd.DataFrame({"Fascia":["F1","F2","F3","TOTALE"],"Energia (kWh)":[c1,c2,c3,c_tot],"Prezzo (€/kWh)":[f1_p,f2_p,f3_p,None],"Totale (€)":[s1,s2,s3,s1+s2+s3]})
                st.table(res.style.format({'Energia (kWh)':'{:.2f}','Prezzo (€/kWh)':'{:.6f}','Totale (€)':'{:.2f}'}, na_rep="-"))
            else: st.error("File GME non trovato")
    except Exception as e: st.error(f"Errore: {e}")
