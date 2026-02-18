
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- MOTOR DE EXTRACCIÓN MEJORADO ---
def motor_sonoscape_v15(texto):
    datos = {k: "No evaluado" for k in ["fey", "ddvi", "dsvi", "sep", "par"]}
    
    # 1. Captura de FEy (El valor 49.19 de Alicia)
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey:
        datos["fey"] = f"{float(match_fey.group(1)):.1f}"
    
    # 2. Captura de medidas anatómicas con corrección de escala (cm a mm)
    medidas_raw = re.findall(r"value\s*=\s*([\d\.]+)\s*displayUnit\s*=\s*mm", texto)
    
    def corregir_medida(valor_str):
        v = float(valor_str)
        # Si el valor es muy pequeño (ej: 0.97), probablemente el ecógrafo se refiere a cm
        return f"{v*10:.1f}" if v < 10 else f"{v:.1f}"

    if len(medidas_raw) >= 3:
        datos["ddvi"] = corregir_medida(medidas_raw[0])
        datos["dsvi"] = corregir_medida(medidas_raw[1])
        datos["sep"] = corregir_medida(medidas_raw[2])
            
    return datos

# --- INTERFAZ ---
st.title("❤️ CardioReport Pro v15")

u_txt = st.file_uploader("1. Subir ALBORNOZTEXT.txt", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Ingresar Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    v = motor_sonoscape_v15(contenido)
    
    st.markdown("### Verificación de Datos (Ajuste Manual si es necesario)")
    col1, col2, col3 = st.columns(3)
    with col1:
        fey_v = st.text_input("FEy (%)", v["fey"])
    with col2:
        # Aquí puedes corregir el 0.97 si ves que en el papel dice otra cosa
        ddvi_v = st.text_input("DDVI (mm)", v["ddvi"])
    with col3:
        sep_v = st.text_input("Septum (mm)", v["sep"])

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=api_key)
        prompt = f"""
        ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE. 
        Redacta el informe para ALICIA ALBORNOZ.
        
        VALORES A USAR:
        - Fracción de Eyección: {fey_v}%
        - Diámetro Diastólico (DDVI): {ddvi_v} mm
        - Septum Interventricular: {sep_v} mm
        
        INSTRUCCIONES DE REDACCIÓN:
        - Si FEy < 55%: Indicar "Disfunción sistólica del ventrículo izquierdo".
        - Si el DDVI o Septum parecen erróneos (ej: muy bajos), redactar como "Evaluados mediante ecografía bidimensional sin particularidades".
        - Formato profesional médico: I. Anatomía, II. Función, III. Hemodinámica, IV. Conclusión.
        """
        
        # ... (Resto del código de envío a Groq y descarga de Word que ya funciona)
