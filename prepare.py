"""
prepare.py - Data fetching, universe, sectors, and backtest harness
for Indian stock momentum strategy.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Config ─────────────────────────────────────────────────────
DATA_START = "2015-01-01"
TEST_START = "2023-01-01"
TEST_END = "2026-03-25"
BENCHMARK_TICKER = "^NSEI"
CACHE_DIR = Path.home() / ".cache" / "mom-autosearch"
RISK_FREE_RATE = 0.07  # 7% annual (India)

# ── Stock Universe (official Nifty 500 from NSE, Mar 2025) ─────

NIFTY_500 = [
    "360ONE.NS", "3MINDIA.NS", "AADHARHFC.NS", "AARTIIND.NS", "AAVAS.NS", "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS",
    "ABFRL.NS", "ABLBL.NS", "ABREL.NS", "ABSLAMC.NS", "ACC.NS", "ACE.NS", "ACMESOLAR.NS", "ADANIENSOL.NS",
    "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", "AEGISLOG.NS", "AEGISVOPAK.NS", "AFCONS.NS", "AFFLE.NS",
    "AGARWALEYE.NS", "AIAENG.NS", "AIIL.NS", "AJANTPHARM.NS", "AKUMS.NS", "AKZOINDIA.NS", "ALKEM.NS", "ALKYLAMINE.NS",
    "ALOKINDS.NS", "AMBER.NS", "AMBUJACEM.NS", "ANANDRATHI.NS", "ANANTRAJ.NS", "ANGELONE.NS", "APARINDS.NS", "APLAPOLLO.NS",
    "APLLTD.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "APTUS.NS", "ARE&M.NS", "ASAHIINDIA.NS", "ASHOKLEY.NS", "ASIANPAINT.NS",
    "ASTERDM.NS", "ASTRAL.NS", "ASTRAZEN.NS", "ATGL.NS", "ATHERENERG.NS", "ATUL.NS", "AUBANK.NS", "AUROPHARMA.NS",
    "AWL.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJAJHFL.NS", "BAJAJHLDNG.NS", "BAJFINANCE.NS", "BALKRISIND.NS",
    "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS", "BASF.NS", "BATAINDIA.NS", "BAYERCROP.NS", "BBTC.NS",
    "BDL.NS", "BEL.NS", "BEML.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHARTIHEXA.NS", "BHEL.NS",
    "BIKAJI.NS", "BIOCON.NS", "BLS.NS", "BLUEDART.NS", "BLUEJET.NS", "BLUESTARCO.NS", "BOSCHLTD.NS", "BPCL.NS",
    "BRIGADE.NS", "BRITANNIA.NS", "BSE.NS", "BSOFT.NS", "CAMPUS.NS", "CAMS.NS", "CANBK.NS", "CANFINHOME.NS",
    "CAPLIPOINT.NS", "CARBORUNIV.NS", "CASTROLIND.NS", "CCL.NS", "CDSL.NS", "CEATLTD.NS", "CENTRALBK.NS", "CENTURYPLY.NS",
    "CERA.NS", "CESC.NS", "CGCL.NS", "CGPOWER.NS", "CHALET.NS", "CHAMBLFERT.NS", "CHENNPETRO.NS", "CHOICEIN.NS",
    "CHOLAFIN.NS", "CHOLAHLDNG.NS", "CIPLA.NS", "CLEAN.NS", "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "COHANCE.NS",
    "COLPAL.NS", "CONCOR.NS", "CONCORDBIO.NS", "COROMANDEL.NS", "CRAFTSMAN.NS", "CREDITACC.NS", "CRISIL.NS", "CROMPTON.NS",
    "CUB.NS", "CUMMINSIND.NS", "CYIENT.NS", "DABUR.NS", "DALBHARAT.NS", "DATAPATTNS.NS", "DBREALTY.NS", "DCMSHRIRAM.NS",
    "DEEPAKFERT.NS", "DEEPAKNTR.NS", "DELHIVERY.NS", "DEVYANI.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DMART.NS",
    "DOMS.NS", "DRREDDY.NS", "ECLERX.NS", "EICHERMOT.NS", "EIDPARRY.NS", "EIHOTEL.NS", "ELECON.NS", "ELGIEQUIP.NS",
    "EMAMILTD.NS", "EMCURE.NS", "ENDURANCE.NS", "ENGINERSIN.NS", "ENRIN.NS", "ERIS.NS", "ESCORTS.NS", "ETERNAL.NS",
    "EXIDEIND.NS", "FACT.NS", "FEDERALBNK.NS", "FINCABLES.NS", "FINPIPE.NS", "FIRSTCRY.NS", "FIVESTAR.NS", "FLUOROCHEM.NS",
    "FORCEMOT.NS", "FORTIS.NS", "FSL.NS", "GAIL.NS", "GESHIP.NS", "GICRE.NS", "GILLETTE.NS", "GLAND.NS",
    "GLAXO.NS", "GLENMARK.NS", "GMDCLTD.NS", "GMRAIRPORT.NS", "GODFRYPHLP.NS", "GODIGIT.NS", "GODREJAGRO.NS", "GODREJCP.NS",
    "GODREJIND.NS", "GODREJPROP.NS", "GPIL.NS", "GRANULES.NS", "GRAPHITE.NS", "GRASIM.NS", "GRAVITA.NS", "GRSE.NS",
    "GSPL.NS", "GUJGASLTD.NS", "GVT&D.NS", "HAL.NS", "HAPPSTMNDS.NS", "HAVELLS.NS", "HBLENGINE.NS", "HCLTECH.NS",
    "HDFCAMC.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEG.NS", "HEROMOTOCO.NS", "HEXT.NS", "HFCL.NS", "HINDALCO.NS",
    "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", "HINDZINC.NS", "HOMEFIRST.NS", "HONASA.NS", "HONAUT.NS", "HSCL.NS",
    "HUDCO.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDBI.NS", "IDEA.NS", "IDFCFIRSTB.NS",
    "IEX.NS", "IFCI.NS", "IGIL.NS", "IGL.NS", "IIFL.NS", "IKS.NS", "INDGN.NS", "INDHOTEL.NS",
    "INDIACEM.NS", "INDIAMART.NS", "INDIANB.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "INOXINDIA.NS",
    "INOXWIND.NS", "INTELLECT.NS", "IOB.NS", "IOC.NS", "IPCALAB.NS", "IRB.NS", "IRCON.NS", "IRCTC.NS",
    "IREDA.NS", "IRFC.NS", "ITC.NS", "ITCHOTELS.NS", "ITI.NS", "J&KBANK.NS", "JBCHEPHARM.NS", "JBMA.NS",
    "JINDALSAW.NS", "JINDALSTEL.NS", "JIOFIN.NS", "JKCEMENT.NS", "JKTYRE.NS", "JMFINANCIL.NS", "JPPOWER.NS", "JSL.NS",
    "JSWCEMENT.NS", "JSWENERGY.NS", "JSWINFRA.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "JUBLINGREA.NS", "JUBLPHARMA.NS", "JWL.NS",
    "JYOTHYLAB.NS", "JYOTICNC.NS", "KAJARIACER.NS", "KALYANKJIL.NS", "KARURVYSYA.NS", "KAYNES.NS", "KEC.NS", "KEI.NS",
    "KFINTECH.NS", "KIMS.NS", "KIRLOSBROS.NS", "KIRLOSENG.NS", "KOTAKBANK.NS", "KPIL.NS", "KPITTECH.NS", "KPRMILL.NS",
    "KSB.NS", "LALPATHLAB.NS", "LATENTVIEW.NS", "LAURUSLABS.NS", "LEMONTREE.NS", "LICHSGFIN.NS", "LICI.NS", "LINDEINDIA.NS",
    "LLOYDSME.NS", "LODHA.NS", "LT.NS", "LTF.NS", "LTFOODS.NS", "LTM.NS", "LTTS.NS", "LUPIN.NS",
    "M&M.NS", "M&MFIN.NS", "MAHABANK.NS", "MAHSCOOTER.NS", "MAHSEAMLES.NS", "MANAPPURAM.NS", "MANKIND.NS", "MANYAVAR.NS",
    "MAPMYINDIA.NS", "MARICO.NS", "MARUTI.NS", "MAXHEALTH.NS", "MAZDOCK.NS", "MCX.NS", "MEDANTA.NS", "METROPOLIS.NS",
    "MFSL.NS", "MGL.NS", "MINDACORP.NS", "MMTC.NS", "MOTHERSON.NS", "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS",
    "MRPL.NS", "MSUMI.NS", "MUTHOOTFIN.NS", "NAM-INDIA.NS", "NATCOPHARM.NS", "NATIONALUM.NS", "NAUKRI.NS", "NAVA.NS",
    "NAVINFLUOR.NS", "NBCC.NS", "NCC.NS", "NESTLEIND.NS", "NETWEB.NS", "NEULANDLAB.NS", "NEWGEN.NS", "NH.NS",
    "NHPC.NS", "NIACL.NS", "NIVABUPA.NS", "NLCINDIA.NS", "NMDC.NS", "NSLNISP.NS", "NTPC.NS", "NTPCGREEN.NS",
    "NUVAMA.NS", "NUVOCO.NS", "NYKAA.NS", "OBEROIRLTY.NS", "OFSS.NS", "OIL.NS", "OLAELEC.NS", "OLECTRA.NS",
    "ONESOURCE.NS", "ONGC.NS", "PAGEIND.NS", "PATANJALI.NS", "PAYTM.NS", "PCBL.NS", "PERSISTENT.NS", "PETRONET.NS",
    "PFC.NS", "PFIZER.NS", "PGEL.NS", "PGHH.NS", "PHOENIXLTD.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS",
    "PNBHOUSING.NS", "POLICYBZR.NS", "POLYCAB.NS", "POLYMED.NS", "POONAWALLA.NS", "POWERGRID.NS", "POWERINDIA.NS", "PPLPHARMA.NS",
    "PRAJIND.NS", "PREMIERENE.NS", "PRESTIGE.NS", "PTCIL.NS", "PVRINOX.NS", "RADICO.NS", "RAILTEL.NS", "RAINBOW.NS",
    "RAMCOCEM.NS", "RBLBANK.NS", "RCF.NS", "RECLTD.NS", "REDINGTON.NS", "RELIANCE.NS", "RELINFRA.NS", "RHIM.NS",
    "RITES.NS", "RKFORGE.NS", "RPOWER.NS", "RRKABEL.NS", "RVNL.NS", "SAGILITY.NS", "SAIL.NS", "SAILIFE.NS",
    "SAMMAANCAP.NS", "SAPPHIRE.NS", "SARDAEN.NS", "SAREGAMA.NS", "SBFC.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS",
    "SCHAEFFLER.NS", "SCHNEIDER.NS", "SCI.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SHYAMMETL.NS", "SIEMENS.NS", "SIGNATURE.NS",
    "SJVN.NS", "SOBHA.NS", "SOLARINDS.NS", "SONACOMS.NS", "SONATSOFTW.NS", "SRF.NS", "STARHEALTH.NS", "SUMICHEM.NS",
    "SUNDARMFIN.NS", "SUNDRMFAST.NS", "SUNPHARMA.NS", "SUNTV.NS", "SUPREMEIND.NS", "SUZLON.NS", "SWANCORP.NS", "SWIGGY.NS",
    "SYNGENE.NS", "SYRMA.NS", "TARIL.NS", "TATACHEM.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAINVEST.NS",
    "TATAPOWER.NS", "TATASTEEL.NS", "TATATECH.NS", "TBOTEK.NS", "TCS.NS", "TECHM.NS", "TECHNOE.NS", "TEJASNET.NS",
    "THELEELA.NS", "THERMAX.NS", "TIINDIA.NS", "TIMKEN.NS", "TITAGARH.NS", "TITAN.NS", "TMPV.NS", "TORNTPHARM.NS",
    "TORNTPOWER.NS", "TRENT.NS", "TRIDENT.NS", "TRITURBINE.NS", "TRIVENI.NS", "TTML.NS", "TVSMOTOR.NS", "UBL.NS",
    "UCOBANK.NS", "ULTRACEMCO.NS", "UNIONBANK.NS", "UNITDSPR.NS", "UNOMINDA.NS", "UPL.NS", "USHAMART.NS", "UTIAMC.NS",
    "VBL.NS", "VEDL.NS", "VENTIVE.NS", "VGUARD.NS", "VIJAYA.NS", "VMM.NS", "VOLTAS.NS", "VTL.NS",
    "WAAREEENER.NS", "WELCORP.NS", "WELSPUNLIV.NS", "WHIRLPOOL.NS", "WIPRO.NS", "WOCKPHARMA.NS", "YESBANK.NS", "ZEEL.NS",
    "ZENSARTECH.NS", "ZENTEC.NS", "ZFCVINDIA.NS", "ZYDUSLIFE.NS",
]

UNIVERSE = NIFTY_500

# ── Sector Mapping ─────────────────────────────────────────────

SECTOR_MAP = {
    # Automobile and Auto Components
    "APOLLOTYRE.NS": "Auto", "ARE&M.NS": "Auto", "ASAHIINDIA.NS": "Auto",
    "ATHERENERG.NS": "Auto", "BAJAJ-AUTO.NS": "Auto", "BALKRISIND.NS": "Auto",
    "BHARATFORG.NS": "Auto", "BOSCHLTD.NS": "Auto", "CEATLTD.NS": "Auto",
    "CRAFTSMAN.NS": "Auto", "EICHERMOT.NS": "Auto", "ENDURANCE.NS": "Auto",
    "EXIDEIND.NS": "Auto", "FORCEMOT.NS": "Auto", "HEROMOTOCO.NS": "Auto",
    "HYUNDAI.NS": "Auto", "JBMA.NS": "Auto", "JKTYRE.NS": "Auto",
    "M&M.NS": "Auto", "MARUTI.NS": "Auto", "MINDACORP.NS": "Auto",
    "MOTHERSON.NS": "Auto", "MRF.NS": "Auto", "MSUMI.NS": "Auto",
    "OLAELEC.NS": "Auto", "OLECTRA.NS": "Auto", "RKFORGE.NS": "Auto",
    "SCHAEFFLER.NS": "Auto", "SONACOMS.NS": "Auto", "SUNDRMFAST.NS": "Auto",
    "TIINDIA.NS": "Auto", "TMPV.NS": "Auto", "TVSMOTOR.NS": "Auto",
    "UNOMINDA.NS": "Auto", "ZFCVINDIA.NS": "Auto",
    # Capital Goods
    "ABB.NS": "Capital Goods", "ACE.NS": "Capital Goods", "AIAENG.NS": "Capital Goods",
    "APARINDS.NS": "Capital Goods", "APLAPOLLO.NS": "Capital Goods", "ASHOKLEY.NS": "Capital Goods",
    "ASTRAL.NS": "Capital Goods", "BDL.NS": "Capital Goods", "BEL.NS": "Capital Goods",
    "BEML.NS": "Capital Goods", "BHEL.NS": "Capital Goods", "CARBORUNIV.NS": "Capital Goods",
    "CGPOWER.NS": "Capital Goods", "COCHINSHIP.NS": "Capital Goods", "CUMMINSIND.NS": "Capital Goods",
    "DATAPATTNS.NS": "Capital Goods", "ELECON.NS": "Capital Goods", "ELGIEQUIP.NS": "Capital Goods",
    "ENRIN.NS": "Capital Goods", "ESCORTS.NS": "Capital Goods", "FINCABLES.NS": "Capital Goods",
    "FINPIPE.NS": "Capital Goods", "GPIL.NS": "Capital Goods", "GRAPHITE.NS": "Capital Goods",
    "GRSE.NS": "Capital Goods", "GVT&D.NS": "Capital Goods", "HAL.NS": "Capital Goods",
    "HBLENGINE.NS": "Capital Goods", "HEG.NS": "Capital Goods", "HONAUT.NS": "Capital Goods",
    "INOXINDIA.NS": "Capital Goods", "INOXWIND.NS": "Capital Goods", "JINDALSAW.NS": "Capital Goods",
    "JWL.NS": "Capital Goods", "JYOTICNC.NS": "Capital Goods", "KAYNES.NS": "Capital Goods",
    "KEI.NS": "Capital Goods", "KIRLOSBROS.NS": "Capital Goods", "KIRLOSENG.NS": "Capital Goods",
    "KSB.NS": "Capital Goods", "MAHSEAMLES.NS": "Capital Goods", "MAZDOCK.NS": "Capital Goods",
    "POLYCAB.NS": "Capital Goods", "POWERINDIA.NS": "Capital Goods", "PRAJIND.NS": "Capital Goods",
    "PREMIERENE.NS": "Capital Goods", "PTCIL.NS": "Capital Goods", "RHIM.NS": "Capital Goods",
    "RRKABEL.NS": "Capital Goods", "SCHNEIDER.NS": "Capital Goods", "SHYAMMETL.NS": "Capital Goods",
    "SIEMENS.NS": "Capital Goods", "SUPREMEIND.NS": "Capital Goods", "SUZLON.NS": "Capital Goods",
    "SYRMA.NS": "Capital Goods", "TARIL.NS": "Capital Goods", "THERMAX.NS": "Capital Goods",
    "TIMKEN.NS": "Capital Goods", "TITAGARH.NS": "Capital Goods", "TRITURBINE.NS": "Capital Goods",
    "USHAMART.NS": "Capital Goods", "WAAREEENER.NS": "Capital Goods", "WELCORP.NS": "Capital Goods",
    "ZENTEC.NS": "Capital Goods",
    # Chemicals
    "AARTIIND.NS": "Chemicals", "ALKYLAMINE.NS": "Chemicals", "ATUL.NS": "Chemicals",
    "BASF.NS": "Chemicals", "BAYERCROP.NS": "Chemicals", "CHAMBLFERT.NS": "Chemicals",
    "CLEAN.NS": "Chemicals", "COROMANDEL.NS": "Chemicals", "DEEPAKFERT.NS": "Chemicals",
    "DEEPAKNTR.NS": "Chemicals", "FACT.NS": "Chemicals", "FLUOROCHEM.NS": "Chemicals",
    "HSCL.NS": "Chemicals", "JUBLINGREA.NS": "Chemicals", "LINDEINDIA.NS": "Chemicals",
    "NAVINFLUOR.NS": "Chemicals", "PCBL.NS": "Chemicals", "PIDILITIND.NS": "Chemicals",
    "PIIND.NS": "Chemicals", "RCF.NS": "Chemicals", "SOLARINDS.NS": "Chemicals",
    "SRF.NS": "Chemicals", "SUMICHEM.NS": "Chemicals", "SWANCORP.NS": "Chemicals",
    "TATACHEM.NS": "Chemicals", "UPL.NS": "Chemicals",
    # Construction
    "AFCONS.NS": "Construction", "ENGINERSIN.NS": "Construction", "IRB.NS": "Construction",
    "IRCON.NS": "Construction", "KEC.NS": "Construction", "KPIL.NS": "Construction",
    "LT.NS": "Construction", "NBCC.NS": "Construction", "NCC.NS": "Construction",
    "RITES.NS": "Construction", "RVNL.NS": "Construction", "TECHNOE.NS": "Construction",
    # Construction Materials
    "ACC.NS": "Cement", "AMBUJACEM.NS": "Cement", "DALBHARAT.NS": "Cement",
    "GRASIM.NS": "Cement", "INDIACEM.NS": "Cement", "JKCEMENT.NS": "Cement",
    "JSWCEMENT.NS": "Cement", "NUVOCO.NS": "Cement", "RAMCOCEM.NS": "Cement",
    "SHREECEM.NS": "Cement", "ULTRACEMCO.NS": "Cement",
    # Consumer Durables
    "AKZOINDIA.NS": "Consumer Durables", "AMBER.NS": "Consumer Durables",
    "ASIANPAINT.NS": "Consumer Durables", "BATAINDIA.NS": "Consumer Durables",
    "BERGEPAINT.NS": "Consumer Durables", "BLUESTARCO.NS": "Consumer Durables",
    "CAMPUS.NS": "Consumer Durables", "CENTURYPLY.NS": "Consumer Durables",
    "CERA.NS": "Consumer Durables", "CROMPTON.NS": "Consumer Durables",
    "DIXON.NS": "Consumer Durables", "HAVELLS.NS": "Consumer Durables",
    "KAJARIACER.NS": "Consumer Durables", "KALYANKJIL.NS": "Consumer Durables",
    "PGEL.NS": "Consumer Durables", "TITAN.NS": "Consumer Durables",
    "VGUARD.NS": "Consumer Durables", "VOLTAS.NS": "Consumer Durables",
    "WHIRLPOOL.NS": "Consumer Durables",
    # Consumer Services
    "ABFRL.NS": "Consumer Services", "ABLBL.NS": "Consumer Services",
    "BLS.NS": "Consumer Services", "CHALET.NS": "Consumer Services",
    "DBREALTY.NS": "Consumer Services", "DEVYANI.NS": "Consumer Services",
    "DMART.NS": "Consumer Services", "EIHOTEL.NS": "Consumer Services",
    "ETERNAL.NS": "Consumer Services", "FIRSTCRY.NS": "Consumer Services",
    "INDHOTEL.NS": "Consumer Services", "INDIAMART.NS": "Consumer Services",
    "IRCTC.NS": "Consumer Services", "ITCHOTELS.NS": "Consumer Services",
    "JUBLFOOD.NS": "Consumer Services", "LEMONTREE.NS": "Consumer Services",
    "MANYAVAR.NS": "Consumer Services", "NAUKRI.NS": "Consumer Services",
    "NYKAA.NS": "Consumer Services", "SAPPHIRE.NS": "Consumer Services",
    "SWIGGY.NS": "Consumer Services", "TBOTEK.NS": "Consumer Services",
    "THELEELA.NS": "Consumer Services", "TRENT.NS": "Consumer Services",
    "VENTIVE.NS": "Consumer Services", "VMM.NS": "Consumer Services",
    # FMCG
    "AWL.NS": "FMCG", "BALRAMCHIN.NS": "FMCG", "BBTC.NS": "FMCG",
    "BIKAJI.NS": "FMCG", "BRITANNIA.NS": "FMCG", "CCL.NS": "FMCG",
    "COLPAL.NS": "FMCG", "DABUR.NS": "FMCG", "DOMS.NS": "FMCG",
    "EIDPARRY.NS": "FMCG", "EMAMILTD.NS": "FMCG", "GILLETTE.NS": "FMCG",
    "GODFRYPHLP.NS": "FMCG", "GODREJAGRO.NS": "FMCG", "GODREJCP.NS": "FMCG",
    "HINDUNILVR.NS": "FMCG", "HONASA.NS": "FMCG", "ITC.NS": "FMCG",
    "JYOTHYLAB.NS": "FMCG", "LTFOODS.NS": "FMCG", "MARICO.NS": "FMCG",
    "NESTLEIND.NS": "FMCG", "PATANJALI.NS": "FMCG", "PGHH.NS": "FMCG",
    "RADICO.NS": "FMCG", "TATACONSUM.NS": "FMCG", "TRIVENI.NS": "FMCG",
    "UBL.NS": "FMCG", "UNITDSPR.NS": "FMCG", "VBL.NS": "FMCG",
    # Financial Services
    "360ONE.NS": "Financial Services", "AADHARHFC.NS": "Financial Services",
    "AAVAS.NS": "Financial Services", "ABCAPITAL.NS": "Financial Services",
    "ABSLAMC.NS": "Financial Services", "AIIL.NS": "Financial Services",
    "ANANDRATHI.NS": "Financial Services", "ANGELONE.NS": "Financial Services",
    "APTUS.NS": "Financial Services", "AUBANK.NS": "Financial Services",
    "AXISBANK.NS": "Financial Services", "BAJAJFINSV.NS": "Financial Services",
    "BAJAJHFL.NS": "Financial Services", "BAJAJHLDNG.NS": "Financial Services",
    "BAJFINANCE.NS": "Financial Services", "BANDHANBNK.NS": "Financial Services",
    "BANKBARODA.NS": "Financial Services", "BANKINDIA.NS": "Financial Services",
    "BSE.NS": "Financial Services", "CAMS.NS": "Financial Services",
    "CANBK.NS": "Financial Services", "CANFINHOME.NS": "Financial Services",
    "CDSL.NS": "Financial Services", "CENTRALBK.NS": "Financial Services",
    "CGCL.NS": "Financial Services", "CHOICEIN.NS": "Financial Services",
    "CHOLAFIN.NS": "Financial Services", "CHOLAHLDNG.NS": "Financial Services",
    "CREDITACC.NS": "Financial Services", "CRISIL.NS": "Financial Services",
    "CUB.NS": "Financial Services", "FEDERALBNK.NS": "Financial Services",
    "FIVESTAR.NS": "Financial Services", "GICRE.NS": "Financial Services",
    "GODIGIT.NS": "Financial Services", "HDFCAMC.NS": "Financial Services",
    "HDFCBANK.NS": "Financial Services", "HDFCLIFE.NS": "Financial Services",
    "HOMEFIRST.NS": "Financial Services", "HUDCO.NS": "Financial Services",
    "ICICIBANK.NS": "Financial Services", "ICICIGI.NS": "Financial Services",
    "ICICIPRULI.NS": "Financial Services", "IDBI.NS": "Financial Services",
    "IDFCFIRSTB.NS": "Financial Services", "IEX.NS": "Financial Services",
    "IFCI.NS": "Financial Services", "IIFL.NS": "Financial Services",
    "INDIANB.NS": "Financial Services", "INDUSINDBK.NS": "Financial Services",
    "IOB.NS": "Financial Services", "IREDA.NS": "Financial Services",
    "IRFC.NS": "Financial Services", "J&KBANK.NS": "Financial Services",
    "JIOFIN.NS": "Financial Services", "JMFINANCIL.NS": "Financial Services",
    "KARURVYSYA.NS": "Financial Services", "KFINTECH.NS": "Financial Services",
    "KOTAKBANK.NS": "Financial Services", "LICHSGFIN.NS": "Financial Services",
    "LICI.NS": "Financial Services", "LTF.NS": "Financial Services",
    "M&MFIN.NS": "Financial Services", "MAHABANK.NS": "Financial Services",
    "MAHSCOOTER.NS": "Financial Services", "MANAPPURAM.NS": "Financial Services",
    "MCX.NS": "Financial Services", "MFSL.NS": "Financial Services",
    "MOTILALOFS.NS": "Financial Services", "MUTHOOTFIN.NS": "Financial Services",
    "NAM-INDIA.NS": "Financial Services", "NIACL.NS": "Financial Services",
    "NIVABUPA.NS": "Financial Services", "NUVAMA.NS": "Financial Services",
    "PAYTM.NS": "Financial Services", "PFC.NS": "Financial Services",
    "PNB.NS": "Financial Services", "PNBHOUSING.NS": "Financial Services",
    "POLICYBZR.NS": "Financial Services", "POONAWALLA.NS": "Financial Services",
    "RBLBANK.NS": "Financial Services", "RECLTD.NS": "Financial Services",
    "SAMMAANCAP.NS": "Financial Services", "SBFC.NS": "Financial Services",
    "SBICARD.NS": "Financial Services", "SBILIFE.NS": "Financial Services",
    "SBIN.NS": "Financial Services", "SHRIRAMFIN.NS": "Financial Services",
    "STARHEALTH.NS": "Financial Services", "SUNDARMFIN.NS": "Financial Services",
    "TATAINVEST.NS": "Financial Services", "UCOBANK.NS": "Financial Services",
    "UNIONBANK.NS": "Financial Services", "UTIAMC.NS": "Financial Services",
    "YESBANK.NS": "Financial Services",
    # Healthcare
    "ABBOTINDIA.NS": "Healthcare", "AGARWALEYE.NS": "Healthcare",
    "AJANTPHARM.NS": "Healthcare", "AKUMS.NS": "Healthcare",
    "ALKEM.NS": "Healthcare", "APLLTD.NS": "Healthcare",
    "APOLLOHOSP.NS": "Healthcare", "ASTERDM.NS": "Healthcare",
    "ASTRAZEN.NS": "Healthcare", "AUROPHARMA.NS": "Healthcare",
    "BIOCON.NS": "Healthcare", "BLUEJET.NS": "Healthcare",
    "CAPLIPOINT.NS": "Healthcare", "CIPLA.NS": "Healthcare",
    "COHANCE.NS": "Healthcare", "CONCORDBIO.NS": "Healthcare",
    "DIVISLAB.NS": "Healthcare", "DRREDDY.NS": "Healthcare",
    "EMCURE.NS": "Healthcare", "ERIS.NS": "Healthcare",
    "FORTIS.NS": "Healthcare", "GLAND.NS": "Healthcare",
    "GLAXO.NS": "Healthcare", "GLENMARK.NS": "Healthcare",
    "GRANULES.NS": "Healthcare", "INDGN.NS": "Healthcare",
    "IPCALAB.NS": "Healthcare", "JBCHEPHARM.NS": "Healthcare",
    "JUBLPHARMA.NS": "Healthcare", "KIMS.NS": "Healthcare",
    "LALPATHLAB.NS": "Healthcare", "LAURUSLABS.NS": "Healthcare",
    "LUPIN.NS": "Healthcare", "MANKIND.NS": "Healthcare",
    "MAXHEALTH.NS": "Healthcare", "MEDANTA.NS": "Healthcare",
    "METROPOLIS.NS": "Healthcare", "NATCOPHARM.NS": "Healthcare",
    "NEULANDLAB.NS": "Healthcare", "NH.NS": "Healthcare",
    "ONESOURCE.NS": "Healthcare", "PFIZER.NS": "Healthcare",
    "POLYMED.NS": "Healthcare", "PPLPHARMA.NS": "Healthcare",
    "RAINBOW.NS": "Healthcare", "SAILIFE.NS": "Healthcare",
    "SUNPHARMA.NS": "Healthcare", "SYNGENE.NS": "Healthcare",
    "TORNTPHARM.NS": "Healthcare", "VIJAYA.NS": "Healthcare",
    "WOCKPHARMA.NS": "Healthcare", "ZYDUSLIFE.NS": "Healthcare",
    # Information Technology
    "AFFLE.NS": "IT", "BSOFT.NS": "IT", "COFORGE.NS": "IT",
    "CYIENT.NS": "IT", "HAPPSTMNDS.NS": "IT", "HCLTECH.NS": "IT",
    "HEXT.NS": "IT", "IKS.NS": "IT", "INFY.NS": "IT",
    "INTELLECT.NS": "IT", "KPITTECH.NS": "IT", "LATENTVIEW.NS": "IT",
    "LTM.NS": "IT", "LTTS.NS": "IT", "MAPMYINDIA.NS": "IT",
    "MPHASIS.NS": "IT", "NETWEB.NS": "IT", "NEWGEN.NS": "IT",
    "OFSS.NS": "IT", "PERSISTENT.NS": "IT", "SAGILITY.NS": "IT",
    "SONATSOFTW.NS": "IT", "TATAELXSI.NS": "IT", "TATATECH.NS": "IT",
    "TCS.NS": "IT", "TECHM.NS": "IT", "WIPRO.NS": "IT",
    "ZENSARTECH.NS": "IT",
    # Media
    "PVRINOX.NS": "Media", "SAREGAMA.NS": "Media", "SUNTV.NS": "Media", "ZEEL.NS": "Media",
    # Metals & Mining
    "ADANIENT.NS": "Metals", "GMDCLTD.NS": "Metals", "GRAVITA.NS": "Metals",
    "HINDALCO.NS": "Metals", "HINDCOPPER.NS": "Metals", "HINDZINC.NS": "Metals",
    "JINDALSTEL.NS": "Metals", "JSL.NS": "Metals", "JSWSTEEL.NS": "Metals",
    "LLOYDSME.NS": "Metals", "NATIONALUM.NS": "Metals", "NMDC.NS": "Metals",
    "NSLNISP.NS": "Metals", "SAIL.NS": "Metals", "SARDAEN.NS": "Metals",
    "TATASTEEL.NS": "Metals", "VEDL.NS": "Metals",
    # Oil Gas & Consumable Fuels
    "AEGISLOG.NS": "Oil & Gas", "AEGISVOPAK.NS": "Oil & Gas", "ATGL.NS": "Oil & Gas",
    "BPCL.NS": "Oil & Gas", "CASTROLIND.NS": "Oil & Gas", "CHENNPETRO.NS": "Oil & Gas",
    "COALINDIA.NS": "Oil & Gas", "GAIL.NS": "Oil & Gas", "GSPL.NS": "Oil & Gas",
    "GUJGASLTD.NS": "Oil & Gas", "HINDPETRO.NS": "Oil & Gas", "IGL.NS": "Oil & Gas",
    "IOC.NS": "Oil & Gas", "MGL.NS": "Oil & Gas", "MRPL.NS": "Oil & Gas",
    "OIL.NS": "Oil & Gas", "ONGC.NS": "Oil & Gas", "PETRONET.NS": "Oil & Gas",
    "RELIANCE.NS": "Oil & Gas",
    # Power
    "ACMESOLAR.NS": "Power", "ADANIENSOL.NS": "Power", "ADANIGREEN.NS": "Power",
    "ADANIPOWER.NS": "Power", "CESC.NS": "Power", "JPPOWER.NS": "Power",
    "JSWENERGY.NS": "Power", "NAVA.NS": "Power", "NHPC.NS": "Power",
    "NLCINDIA.NS": "Power", "NTPC.NS": "Power", "NTPCGREEN.NS": "Power",
    "POWERGRID.NS": "Power", "RELINFRA.NS": "Power", "RPOWER.NS": "Power",
    "SJVN.NS": "Power", "TATAPOWER.NS": "Power", "TORNTPOWER.NS": "Power",
    # Realty
    "ANANTRAJ.NS": "Realty", "BRIGADE.NS": "Realty", "DLF.NS": "Realty",
    "GODREJPROP.NS": "Realty", "LODHA.NS": "Realty", "OBEROIRLTY.NS": "Realty",
    "PHOENIXLTD.NS": "Realty", "PRESTIGE.NS": "Realty", "SIGNATURE.NS": "Realty",
    "SOBHA.NS": "Realty",
    # Services
    "ADANIPORTS.NS": "Services", "BLUEDART.NS": "Services", "CONCOR.NS": "Services",
    "DELHIVERY.NS": "Services", "ECLERX.NS": "Services", "FSL.NS": "Services",
    "GESHIP.NS": "Services", "GMRAIRPORT.NS": "Services", "IGIL.NS": "Services",
    "INDIGO.NS": "Services", "JSWINFRA.NS": "Services", "MMTC.NS": "Services",
    "REDINGTON.NS": "Services", "SCI.NS": "Services",
    # Telecom
    "BHARTIARTL.NS": "Telecom", "BHARTIHEXA.NS": "Telecom", "HFCL.NS": "Telecom",
    "IDEA.NS": "Telecom", "INDUSTOWER.NS": "Telecom", "ITI.NS": "Telecom",
    "RAILTEL.NS": "Telecom", "TATACOMM.NS": "Telecom", "TEJASNET.NS": "Telecom",
    "TTML.NS": "Telecom",
    # Textiles
    "ALOKINDS.NS": "Textiles", "KPRMILL.NS": "Textiles", "PAGEIND.NS": "Textiles",
    "TRIDENT.NS": "Textiles", "VTL.NS": "Textiles", "WELSPUNLIV.NS": "Textiles",
    # Diversified
    "3MINDIA.NS": "Diversified", "DCMSHRIRAM.NS": "Diversified", "GODREJIND.NS": "Diversified",
    # Forest Materials
    "ABREL.NS": "Forest Materials",
}


def get_sector(ticker):
    return SECTOR_MAP.get(ticker, "Other")


# ── Data Fetching ──────────────────────────────────────────────


def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_data():
    """Download OHLCV for universe + benchmark. Cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "market_data.pkl"

    if cache_file.exists():
        print(f"Loading cached data from {cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    print("Fetching data from Yahoo Finance...")
    all_data = {}
    failed = []
    all_tickers = list(dict.fromkeys(UNIVERSE))

    for ticker in all_tickers:
        try:
            df = yf.download(ticker, start=DATA_START, end=TEST_END, progress=False)
            df = _flatten_columns(df)
            if len(df) >= 252:
                all_data[ticker] = df
                print(f"  OK: {ticker} ({len(df)} rows)")
            else:
                failed.append(ticker)
                print(f"  SKIP: {ticker} (only {len(df)} rows)")
        except Exception as e:
            failed.append(ticker)
            print(f"  FAIL: {ticker} ({e})")

    print(f"Fetching benchmark {BENCHMARK_TICKER}...")
    benchmark = yf.download(BENCHMARK_TICKER, start=DATA_START, end=TEST_END, progress=False)
    benchmark = _flatten_columns(benchmark)

    data = {"stocks": all_data, "benchmark": benchmark}
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)

    print(f"\nFetched {len(all_data)} stocks ({len(failed)} failed)")
    return data


def load_data():
    """Load cached data, return stocks dict + benchmark returns."""
    raw = fetch_data()
    bench = raw["benchmark"]
    bench_ret = bench["Close"].pct_change().dropna()

    # Precompute daily returns for all stocks
    stock_returns = {}
    for ticker, df in raw["stocks"].items():
        stock_returns[ticker] = df["Close"].pct_change()

    print(f"Loaded {len(raw['stocks'])} stocks")
    return {
        "stocks": raw["stocks"],
        "stock_returns": stock_returns,
        "benchmark_returns": bench_ret,
    }


# ── Backtest ───────────────────────────────────────────────────


def evaluate_strategy(holdings_schedule, data):
    """
    Backtest a momentum strategy from a holdings schedule.

    holdings_schedule: list of (pd.Timestamp, list[str])
        Each entry = (rebalance_date, tickers_to_hold).
        Empty list = cash.
    data: output of load_data()

    Returns dict of performance metrics.
    """
    stock_returns = data["stock_returns"]
    bench = data["benchmark_returns"]

    # Build list of all test trading days from benchmark index
    test_start = pd.Timestamp(TEST_START)
    test_dates = sorted([d for d in bench.index if d >= test_start])

    if not test_dates or not holdings_schedule:
        return _empty_metrics()

    risk_free_daily = RISK_FREE_RATE / 252

    # Sort schedule by date
    schedule = sorted(holdings_schedule, key=lambda x: x[0])

    # Walk through each day
    portfolio_returns = []
    ret_dates = []
    current_holdings = []
    sched_idx = 0
    cash_days = 0
    total_holdings_count = 0
    num_rebalances = 0

    for date in test_dates:
        # Check if we need to update holdings
        while sched_idx < len(schedule) and schedule[sched_idx][0] <= date:
            current_holdings = schedule[sched_idx][1]
            sched_idx += 1
            num_rebalances += 1

        if not current_holdings:
            portfolio_returns.append(risk_free_daily)
            cash_days += 1
        else:
            rets = []
            for t in current_holdings:
                if t in stock_returns and date in stock_returns[t].index:
                    r = stock_returns[t].loc[date]
                    if not np.isnan(r):
                        rets.append(r)
            if rets:
                portfolio_returns.append(np.mean(rets))
                total_holdings_count += len(rets)
            else:
                portfolio_returns.append(risk_free_daily)
                cash_days += 1

        ret_dates.append(date)

    port = pd.Series(portfolio_returns, index=pd.DatetimeIndex(ret_dates))
    bench_aligned = bench.reindex(port.index).fillna(0)

    # Sharpe (annualised, 7% risk-free)
    excess = port - risk_free_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0.0

    # Returns
    total_return = ((1 + port).prod() - 1) * 100
    bench_prod = (1 + bench_aligned).prod()
    if hasattr(bench_prod, "__len__"):
        bench_prod = float(bench_prod.iloc[0]) if len(bench_prod) > 0 else 1.0
    bench_return = (float(bench_prod) - 1) * 100

    # Drawdown
    cum = (1 + port).cumprod()
    running_max = cum.cummax()
    dd = (cum - running_max) / running_max
    max_dd = abs(dd.min()) * 100

    # Win rate
    win_rate = (port > 0).mean() * 100

    # Average holdings
    non_cash_days = len(port) - cash_days
    avg_holdings = total_holdings_count / non_cash_days if non_cash_days > 0 else 0

    # Monthly returns for best/worst
    monthly = port.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    return {
        "sharpe_ratio": round(float(sharpe), 4),
        "total_return_pct": round(float(total_return), 1),
        "benchmark_return_pct": round(float(bench_return), 1),
        "alpha_pct": round(float(total_return - bench_return), 1),
        "max_drawdown_pct": round(float(max_dd), 1),
        "win_rate_pct": round(float(win_rate), 1),
        "avg_holdings": round(float(avg_holdings), 1),
        "cash_pct": round(float(cash_days / len(port) * 100), 1),
        "num_rebalances": num_rebalances,
        "trading_days": len(port),
        "best_month_pct": round(float(monthly.max() * 100), 1) if len(monthly) > 0 else 0,
        "worst_month_pct": round(float(monthly.min() * 100), 1) if len(monthly) > 0 else 0,
    }


def _empty_metrics():
    return {k: 0 for k in [
        "sharpe_ratio", "total_return_pct", "benchmark_return_pct",
        "alpha_pct", "max_drawdown_pct", "win_rate_pct", "avg_holdings",
        "cash_pct", "num_rebalances", "trading_days", "best_month_pct",
        "worst_month_pct",
    ]}


def print_results(metrics, elapsed=0):
    """Pretty-print backtest results."""
    print()
    print("=" * 60)
    print("  MOMENTUM STRATEGY RESULTS")
    print("=" * 60)
    print(f"  Sharpe ratio (ann.):   {metrics['sharpe_ratio']:.4f}")
    print(f"  Total return:          {metrics['total_return_pct']:.1f}%")
    print(f"  Benchmark (Nifty 50):  {metrics['benchmark_return_pct']:.1f}%")
    print(f"  Alpha:                 {metrics['alpha_pct']:.1f}%")
    print(f"  Max drawdown:          {metrics['max_drawdown_pct']:.1f}%")
    print(f"  Win rate (daily):      {metrics['win_rate_pct']:.1f}%")
    print(f"  Avg stocks held:       {metrics['avg_holdings']:.1f}")
    print(f"  Cash %:                {metrics['cash_pct']:.1f}%")
    print(f"  Rebalances:            {metrics['num_rebalances']}")
    print(f"  Trading days:          {metrics['trading_days']}")
    print(f"  Best month:            {metrics['best_month_pct']:.1f}%")
    print(f"  Worst month:           {metrics['worst_month_pct']:.1f}%")
    if elapsed:
        print(f"  Runtime:               {elapsed:.1f}s")
    print("=" * 60)

    # Machine-readable block
    print("\n---")
    for k, v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    print("Fetching and caching data...")
    fetch_data()
    print("Done. Run: python strategy.py")
