
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# Configuración API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def buscar_dato_en_toda_la_hoja(df, terminos):
    """Busca cualquier término de la lista en el Excel y devuelve lo que hay a la derecha"""
    for r in range(len(df)):
        for c in range(len(df.columns)):
            celda = str(df.iloc[r, c]).strip().lower()
            for t in terminos:
                if t.lower() in celda:
                    try:
                        # Intentamos tomar el valor de la celda inmediatamente a la derecha
                        res = str(df.iloc[r, c + 1]).strip()
                        if res.lower() != "nan" and res != "" and res.lower() != "none":
                            return res
                    except: pass
    return "N/A"

def extraer_datos_excel_manual(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        # Cargar Excel con soporte para formatos viejos
        xls = pd.ExcelFile(file, engine='xlrd' if file.name.endswith('.xls') else None)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Búsqueda ultra-flexible de datos del paciente
        info["paciente"]["Nombre"] = buscar_dato_en_toda_la_hoja(df_eco, ["Paciente", "Nombre", "BALEIRON"])
        info["paciente"]["Peso"] = buscar_dato_en_toda_la_hoja(df_eco, ["Peso", "Kg"])
        info["paciente"]["Altura"] = buscar_dato_en_toda_la_hoja(df_eco, ["Altura", "Cm"])
        info["paciente"]["BSA"] = buscar_dato_en_toda_la_hoja(df_eco, ["DUBOIS", "Superficie", "SC"])

        # Mediciones técnicas
        mapeo = {
            "DDVI": "Diámetro Diastólico Ventrículo Izquierdo",
            "DSVI": "Diámetro Sistólico Ventrículo Izquierdo",
            "FA": "Fracción de Acortamiento",
            "DDVD": "Ventrículo Derecho",
            "DDAI": "Aurícula Izquierda",
            "DDSIV": "Septum Interventricular",
            "DDPP": "Pared Posterior"
        }
        for sigla, nombre in mapeo.items():
            val = buscar_dato_en_toda_la_hoja(df_eco, [sigla])
            if val != "N/A": 
                info["eco"][nombre] = val

        # Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
    except Exception as e:
        st.error(f"Error en la extracción: {e}")
    return info

def redactar_ia(info):
    prompt = f"""
    Eres un Cardiólogo experto. Redacta un informe médico basado en:
    Mediciones: {info['eco']}
    Doppler: {info['do
