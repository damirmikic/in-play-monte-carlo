import streamlit as st
import numpy as np
import pandas as pd

# -------------------------------------------------------------------
# KORAK 1: KOPIRAMO NAŠU POSTOJEĆU SIMULACIONU FUNKCIJU
# Ova funkcija ostaje ista kao u prethodnom odgovoru.
# -------------------------------------------------------------------

# --- Konstante za podešavanje modela ---
CRVENI_KARTON_NAPAD_PENAL = 0.75
CRVENI_KARTON_ODBRANA_BONUS = 1.15

@st.cache_data
def monte_carlo_soccer_inplay(
    trenutni_minut: int,
    trenutni_golovi_domacin: int,
    trenutni_golovi_gost: int,
    pre_match_xg_domacin: float,
    pre_match_xg_gost: float,
    crveni_kartoni_domacin: int = 0,
    crveni_kartoni_gost: int = 0,
    broj_simulacija: int = 10000
) -> dict:
    
    # --- Osnovni proračuni ---
    preostalo_vreme_procenat = (90 - trenutni_minut) / 90
    if preostalo_vreme_procenat < 0: preostalo_vreme_procenat = 0

    preostali_xg_domacin = pre_match_xg_domacin * preostalo_vreme_procenat
    preostali_xg_gost = pre_match_xg_gost * preostalo_vreme_procenat

    # --- Prilagođavanje za crvene kartone ---
    if crveni_kartoni_domacin > 0:
        preostali_xg_domacin *= (CRVENI_KARTON_NAPAD_PENAL ** crveni_kartoni_domacin)
        preostali_xg_gost *= (CRVENI_KARTON_ODBRANA_BONUS ** crveni_kartoni_domacin)

    if crveni_kartoni_gost > 0:
        preostali_xg_gost *= (CRVENI_KARTON_NAPAD_PENAL ** crveni_kartoni_gost)
        preostali_xg_domacin *= (CRVENI_KARTON_ODBRANA_BONUS ** crveni_kartoni_gost)

    # --- Simulacija ---
    simulirani_golovi_domacin = np.random.poisson(preostali_xg_domacin, broj_simulacija)
    simulirani_golovi_gost = np.random.poisson(preostali_xg_gost, broj_simulacija)

    konacni_golovi_domacin = trenutni_golovi_domacin + simulirani_golovi_domacin
    konacni_golovi_gost = trenutni_golovi_gost + simulirani_golovi_gost
    
    ukupno_golova = konacni_golovi_domacin + konacni_golovi_gost
    
    # --- Proračun verovatnoća za markete ---
    pobeda_domacina = np.sum(konacni_golovi_domacin > konacni_golovi_gost) / broj_simulacija
    nereseno = np.sum(konacni_golovi_domacin == konacni_golovi_gost) / broj_simulacija
    pobeda_gosta = 1 - pobeda_domacina - nereseno
    preko_2_5 = np.sum(ukupno_golova > 2.5) / broj_simulacija
    btts_da = np.sum((konacni_golovi_domacin > 0) & (konacni_golovi_gost > 0)) / broj_simulacija
    
    rezultati, brojanja = np.unique(list(zip(konacni_golovi_domacin, konacni_golovi_gost)), axis=0, return_counts=True)
    sortirani_indeksi = np.argsort(-brojanja)
    tacan_rezultat = {f"{rez[0]}-{rez[1]}": brojanja[i]/broj_simulacija for i, rez in enumerate(rezultati[sortirani_indeksi[:5]])}

    def prob_to_odds(prob):
        return (1 / prob) if prob > 0 else float('inf')

    # --- Kreiranje rečnika koji se vraća ---
    # Ova verzija garantuje da su svi potrebni ključevi uvek prisutni.
    return {
        "1. Konacan Ishod (1X2)": {
            "1": {"prob": pobeda_domacina, "kvota": prob_to_odds(pobeda_domacina)},
            "X": {"prob": nereseno, "kvota": prob_to_odds(nereseno)},
            "2": {"prob": pobeda_gosta, "kvota": prob_to_odds(pobeda_gosta)},
        },
        "2. Ukupno Golova (O/U 2.5)": {
            "Over 2.5": {"prob": preko_2_5, "kvota": prob_to_odds(preko_2_5)},
            "Under 2.5": {"prob": 1 - preko_2_5, "kvota": prob_to_odds(1 - preko_2_5)},
        },
        "3. Oba Tima Daju Gol (BTTS)": {
            "Da": {"prob": btts_da, "kvota": prob_to_odds(btts_da)},
            "Ne": {"prob": 1 - btts_da, "kvota": prob_to_odds(1 - btts_da)},
        },
        "4. Tacan Rezultat (Top 5)": {
           k: {"prob": v, "kvota": prob_to_odds(v)} for k, v in tacan_rezultat.items()
        },
    }


# -------------------------------------------------------------------
# KORAK 2: KREIRANJE STREAMLIT APLIKACIJE
# Ovo je novi deo koda koji pravi web interfejs.
# -------------------------------------------------------------------

st.set_page_config(layout="wide")

st.title("⚽ In-Play Soccer Monte Carlo Simulator")

# --- Sidebar za opšte parametre ---
st.sidebar.header("Opšti Parametri Utakmice")
trenutni_minut = st.sidebar.slider("Trenutni minut", 0, 90, 65)
broj_simulacija = st.sidebar.select_slider(
    "Broj simulacija (više je preciznije, ali sporije)",
    options=[1000, 5000, 10000, 20000, 50000],
    value=10000
)

# --- Glavni deo za unos podataka o timovima ---
st.header("Unesite Podatke o Utakmici")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Domaći Tim")
    domacin_naziv = st.text_input("Naziv domaćeg tima", "Tim A")
    trenutni_golovi_domacin = st.number_input("Trenutni golovi (Domaćin)", min_value=0, step=1, value=1)
    pre_match_xg_domacin = st.number_input("Pre-match xG (Domaćin)", min_value=0.0, step=0.1, value=1.8, format="%.2f")
    crveni_kartoni_domacin = st.number_input("Crveni kartoni (Domaćin)", min_value=0, max_value=4, step=1, value=1)

with col2:
    st.subheader("Gostujući Tim")
    gost_naziv = st.text_input("Naziv gostujućeg tima", "Tim B")
    trenutni_golovi_gost = st.number_input("Trenutni golovi (Gost)", min_value=0, step=1, value=0)
    pre_match_xg_gost = st.number_input("Pre-match xG (Gost)", min_value=0.0, step=0.1, value=1.2, format="%.2f")
    crveni_kartoni_gost = st.number_input("Crveni kartoni (Gost)", min_value=0, max_value=4, step=1, value=0)

# --- Dugme za pokretanje simulacije ---
if st.button("POKRENI SIMULACIJU", use_container_width=True):
    with st.spinner('Simulacija je u toku, molimo sačekajte...'):
        sim_rezultat = monte_carlo_soccer_inplay(
            trenutni_minut=trenutni_minut,
            trenutni_golovi_domacin=trenutni_golovi_domacin,
            trenutni_golovi_gost=trenutni_golovi_gost,
            pre_match_xg_domacin=pre_match_xg_domacin,
            pre_match_xg_gost=pre_match_xg_gost,
            crveni_kartoni_domacin=crveni_kartoni_domacin,
            crveni_kartoni_gost=crveni_kartoni_gost,
            broj_simulacija=broj_simulacija
        )

    st.header("📈 Rezultati Simulacije")
    st.info(f"Trenutni scenario: **{trenutni_minut}' minut, {domacin_naziv} {trenutni_golovi_domacin} - {trenutni_golovi_gost} {gost_naziv}**")

    # --- Prikaz rezultata ---
    res1, res2 = st.columns(2)
    
    with res1:
        st.subheader("Konačan Ishod (1X2)")
        ishod_data = sim_rezultat["1. Konacan Ishod (1X2)"]
        st.metric(label=f"Pobeda {domacin_naziv} (1)", value=f"{ishod_data['1']['kvota']:.2f}", delta=f"{ishod_data['1']['prob']*100:.1f}% verovatnoća")
        st.metric(label="Nerešeno (X)", value=f"{ishod_data['X']['kvota']:.2f}", delta=f"{ishod_data['X']['prob']*100:.1f}% verovatnoća")
        st.metric(label=f"Pobeda {gost_naziv} (2)", value=f"{ishod_data['2']['kvota']:.2f}", delta=f"{ishod_data['2']['prob']*100:.1f}% verovatnoća")
    
    with res2:
        st.subheader("Ukupno Golova (Više/Manje 2.5)")
        ou_data = sim_rezultat["2. Ukupno Golova (O/U 2.5)"]
        st.metric(label="Više od 2.5 gola", value=f"{ou_data['Over 2.5']['kvota']:.2f}", delta=f"{ou_data['Over 2.5']['prob']*100:.1f}% verovatnoća")
        st.metric(label="Manje od 2.5 gola", value=f"{ou_data['Under 2.5']['kvota']:.2f}", delta=f"{ou_data['Under 2.5']['prob']*100:.1f}% verovatnoća")
        
        st.subheader("Oba Tima Daju Gol (BTTS)")
        btts_data = sim_rezultat["3. Oba Tima Daju Gol (BTTS)"]
        st.metric(label="DA", value=f"{btts_data['Da']['kvota']:.2f}", delta=f"{btts_data['Da']['prob']*100:.1f}% verovatnoća")
        st.metric(label="NE", value=f"{btts_data['Ne']['kvota']:.2f}", delta=f"{btts_data['Ne']['prob']*100:.1f}% verovatnoća")

   # ISPRAVLJEN KOD
st.subheader("Tačan Rezultat (Top 5 najverovatnijih)")
cs_data = sim_rezultat["4. Tacan Rezultat (Top 5)"]
df_cs = pd.DataFrame.from_dict(cs_data, orient='index')

# Ispravno preimenovanje DVE kolone
df_cs.columns = ['Verovatnoća', 'Kvota']

# Formatiranje kolona radi lepšeg prikaza
# .map('{:.2%}') je elegantniji način za formatiranje u procente
df_cs['Verovatnoća'] = df_cs['Verovatnoća'].map('{:.2%}'.format) 
df_cs['Kvota'] = df_cs['Kvota'].map('{:,.2f}'.format)

st.table(df_cs)
