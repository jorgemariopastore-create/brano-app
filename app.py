
import streamlit as st
from groq import Groq

# --- 1. CONFIGURACIÓN DE INTERFAZ (LIMPIA Y ESTABLE) ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")
st.markdown("---")

# --- 2. GESTIÓN DE SESIÓN ---
# Mantenemos los datos en memoria para que no se borren al escribir
if "form_datos" not in st.session_state:
    st.session_state.form_datos = {"pac": "", "fec": "", "ddvi": "", "dsvi": "", "siv": "", "pp": "", "fey": ""}
if "informe_final" not in st.session_state:
    st.session_state.informe_final = ""

# --- 3. FORMULARIO DE ENTRADA MANUAL (FIABLE) ---
with st.form("validador_estable"):
    st.subheader("Ingreso de Datos del Paciente")
    
    c1, c2 = st.columns([3, 1])
    pac = c1.text_input("Nombre del Paciente", placeholder="Ej: ALBORNOZ ALICIA")
    fec = c2.text_input("Fecha", placeholder="DD/MM/AAAA")
    
    st.write("---")
    st.markdown("### Parámetros Ecocardiográficos")
    
    
    
    c3, c4, c5, c6, c7 = st.columns(5)
    ddvi = c3.text_input("DDVI (mm)")
    dsvi = c4.text_input("DSVI (mm)")
    siv = c5.text_input("SIV (mm)")
    pp = c6.text_input("PP (mm)")
    fey = c7.text_input("FEy (%)")
    
    st.markdown("---")
    if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
        if not pac or not ddvi:
            st.warning("Por favor, complete al menos el nombre y el DDVI.")
        else:
            # LLAMADA A GROQ CON EL MODELO QUE LE GUSTÓ
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            
            prompt = f"""Actúa como el Dr. Pastore, cardiólogo senior. 
            Redacta un informe médico basado en estos datos:
            Paciente: {pac}, Fecha: {fec}, DDVI: {ddvi}mm, DSVI: {dsvi}mm, SIV: {siv}mm, PP: {pp}mm, FEy: {fey}%.
            
            REGLAS DE FORMATO:
            1. Estilo seco, técnico y profesional.
            2. Texto JUSTIFICADO.
            3. Estructura: HALLAZGOS (motilidad y diámetros), VALVULAS, CONCLUSIÓN.
            4. Sin repetir el nombre del paciente en el cuerpo del texto.
            5. Fuente simulada Arial 12."""
            
            with st.spinner("Redactando con excelencia médica..."):
                res = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[{'role': 'user', 'content': prompt}]
                )
                st.session_state.informe_final = res.choices[0].message.content

# --- 4. ÁREA DE RESULTADO (EL INFORME QUE LE GUSTA) ---
if st.session_state.informe_final:
    st.markdown("---")
    st.subheader("Vista Previa del Informe")
    
    # Caja de texto con formato profesional
    st.info(st.session_state.informe_final)
    
    # Botón para descargar o copiar (opcional)
    st.button("📄 Exportar a Word (Arial 12)")
