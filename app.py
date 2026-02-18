
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- LÓGICA DE EXTRACCIÓN AVANZADA ---

def extract_tech_value(content, tags, is_percent=False):
    """
    Busca el valor numérico más probable para una lista de etiquetas.
    Senior approach: No depende de 'value=', busca el primer float válido tras la etiqueta.
    """
    for tag in tags:
        # Buscamos la etiqueta y capturamos el siguiente número en un radio de 100 caracteres
        pattern = re.compile(rf"{re.escape(tag)}[\s\S]{{0,100}}?([\d\.,]+)", re.I)
        matches = pattern.finditer(content)
        for m in matches:
            val_str = m.group(1).replace(',', '.')
            try:
                val = float(val_str)
                # Filtros de validación médica estricta
                if is_percent:
                    if 15 <= val <= 95: return f"{val:.2f}"
                else:
                    if 0.5 <= val <= 85: return f"{val:.2f}"
            except ValueError:
                continue
    return None

# --- UI Y PROCESAMIENTO ---

st.set_page_config(page_title="CardioReport Pro Senior", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

file_data = st.file_uploader("1. Datos (TXT/DOCX)", type=["txt", "docx"])
file_pdf = st.file_uploader("2. PDF (Imágenes)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if file_data and file_pdf and api_key:
    if st.button("🚀 GENERAR INFORME DE ALTA PRECISIÓN"):
        try:
            # Lectura robusta de archivos
            if file_data.name.endswith('.docx'):
                raw_text = docx2txt.process(file_data)
            else:
                # Intentamos múltiples codificaciones
                raw_bytes = file_data.read()
                try:
                    raw_text = raw_bytes.decode("utf-8")
                except:
                    raw_text = raw_bytes.decode("latin-1", errors="ignore")

            # EXTRACCIÓN QUIRÚRGICA (Python puro)
            data = {
                "ddvi": extract_tech_value(raw_text, ["LVID(d)", "LVIDd", "DDVI", "Diastolic LVID"]),
                "dsvi": extract_tech_value(raw_text, ["LVID(s)", "LVIDs", "DSVI", "Systolic LVID"]),
                "septum": extract_tech_value(raw_text, ["IVS(d)", "IVSd", "DDSIV", "Septum"]),
                "pared": extract_tech_value(raw_text, ["LVPW(d)", "LVPWd", "DDPP", "Pared"]),
                "fey": extract_tech_value(raw_text, ["EF(Teich)", "EF", "FEy", "LVEF"], True),
                "fa": extract_tech_value(raw_text, ["FS(Teich)", "FS", "FA", "Fractional Shortening"], True)
            }

            # IA para redacción médica (Groq)
            client = Groq(api_key=api_key)
            
            # Formateamos los datos para el prompt
            tech_summary = "\n".join([f"{k.upper()}: {v if v else 'No evaluado'}" for k, v in data.items()])
            
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE.
            Usa estos valores técnicos específicos para el informe de ALICIA ALBORNOZ:
            {tech_summary}
            
            Busca datos personales (Edad, Peso, Altura) aquí: {raw_text[:2000]}
            
            ESTRUCTURA:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA
            II. FUNCIÓN VENTRICULAR
            III. EVALUACIÓN HEMODINÁMICA
            IV. CONCLUSIÓN (Si FEy >= 55%: 'Función ventricular izquierda conservada')
            
            IMPORTANTE: No digas 'no se visualiza' si el valor está presente en la lista de arriba.
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            final_report = completion.choices[0].message.content
            st.info(final_report)
            
            # Generación de Word (Firma y tabla de imágenes)
            # [Aquí iría la función generar_docx_profesional que ya tenemos]
            
        except Exception as e:
            st.error(f"Error Senior Parser: {e}")
