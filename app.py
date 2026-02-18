
import streamlit as st
from groq import Groq
import re

def motor_sonoscape_e3(texto):
    """
    Extrae datos del SonoScape E3 basándose en la estructura de bloques técnicos.
    """
    datos = {k: "No evaluado" for k in ["fey", "ddvi", "dsvi", "sep", "par"]}
    
    # 1. Buscamos el valor de FEy (Priorizamos el Bloque de Resultado 1)
    # En Alicia, el valor 49.19 está vinculado a resultNo = 1
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey:
        datos["fey"] = match_fey.group(1)
    
    # 2. Si no aparece como resultNo, buscamos cualquier valor con unidad '%' 
    # que esté en un rango lógico (40-80)
    if datos["fey"] == "No evaluado":
        porcentajes = re.findall(r"value\s*=\s*([\d\.]+)\s*displayUnit\s*=\s*%", texto)
        for p in porcentajes:
            if 15 <= float(p) <= 95:
                datos["fey"] = p
                break

    # 3. Extracción de medidas anatómicas (mm)
    # Buscamos valores que suelen ser diámetros (ej: entre 30 y 60 mm)
    medidas_mm = re.findall(r"value\s*=\s*([\d\.]+)\s*displayUnit\s*=\s*mm", texto)
    if len(medidas_mm) >= 2:
        datos["ddvi"] = medidas_mm[0]
        datos["dsvi"] = medidas_mm[1]
        
    return datos

# --- INTERFAZ ---
st.title("❤️ CardioReport Pro (Optimizado SonoScape E3)")

u_txt = st.file_uploader("Subir ALBORNOZTEXT.txt", type=["txt"])
api_key = st.text_input("Groq API Key", type="password")

if u_txt and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    v = motor_sonoscape_e3(contenido)
    
    # PANEL DE CONTROL PARA EL DR. PASTORE
    st.subheader("Confirmación de Datos del Ecógrafo")
    fey = st.number_input("Fracción de Eyección (%)", value=float(v["fey"]) if v["fey"] != "No evaluado" else 55.0)
    ddvi = st.text_input("DDVI (mm)", v["ddvi"])

    if st.button("Generar Informe Word"):
        # (Aquí va la llamada a Groq y la generación de Word)
        st.success("Informe en proceso con FEy de " + str(fey) + "%")
