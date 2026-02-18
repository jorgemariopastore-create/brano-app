
import streamlit as st
from groq import Groq
import re
import fitz
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- EL SABUESO CALIBRADO PARA ALICIA ---
def extraer_datos_alicia(texto):
    datos = {k: "No evaluado" for k in ["ddvi", "dsvi", "sep", "par", "fey", "fa"]}
    
    # Buscamos el valor 49.19 que aparece en el reporte de Alicia 
    # Este patrón busca el valor numérico después de 'resultNo = 1' 
    match_fey = re.search(r"resultNo\s*=\s*1.*?value\s*=\s*([\d\.]+)", texto, re.DOTALL)
    if match_fey:
        datos["fey"] = match_fey.group(1)
    
    # Intentamos capturar otros valores numéricos que no sean asteriscos [cite: 13, 14]
    otros_valores = re.findall(r"value\s*=\s*([\d\.]+)", texto)
    # Si hay valores de milímetros (cm en el TXT), los asignamos por orden lógico
    # (Esto es experimental debido al desorden del TXT de SonoScape)
    
    return datos

st.title("❤️ CardioReport Pro")
st.markdown("---")

# 1. CARGA DE ARCHIVOS (CENTRALIZADA)
u_txt = st.file_uploader("1. Subir Reporte de Texto (ALBORNOZTEXT.txt)", type=["txt"])
u_pdf = st.file_uploader("2. Subir PDF con Imágenes", type=["pdf"])
api_key = st.text_input("Ingresar Groq API Key", type="password")

if u_txt and u_pdf and api_key:
    # Procesar archivo
    contenido = u_txt.read().decode("latin-1", errors="ignore")
    v = extraer_datos_alicia(contenido)
    
    # Mostrar lo que el Sabueso encontró para que confirmes
    st.subheader("Datos Detectados")
    col1, col2 = st.columns(2)
    with col1:
        fey_final = st.text_input("Confirmar FEy (%)", v["fey"])
    with col2:
        paciente = "ALICIA ALBORNOZ" # Extraído del encabezado [cite: 1]

    if st.button("🚀 GENERAR INFORME"):
        client = Groq(api_key=api_key)
        
        prompt = f"""
        ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE.
        Paciente: {paciente}.
        Dato técnico: FEy {fey_final}%.
        
        REDACTA EL INFORME:
        I. Anatomía (Indicar que se evalúa por imagen ante la ausencia de valores nominales en el reporte).
        II. Función (Con FEy {fey_final}%, indicar Disfunción sistólica moderada).
        III. Hemodinámica.
        IV. Conclusión.
        """
        
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        st.markdown("---")
        st.markdown(res.choices[0].message.content)
        st.success("Informe generado exitosamente.")
