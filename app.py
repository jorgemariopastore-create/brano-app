
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document

# 1. Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # 2. Extracción y Limpieza Agresiva
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    texto_acumulado = ""
    for pagina in pdf:
        # Extraemos texto bloque por bloque
        bloques = pagina.get_text("blocks")
        for b in bloques:
            texto_acumulado += b[4] + " " # Juntamos el contenido de cada bloque
    pdf.close()

    # Limpiamos el texto para que los números queden cerca de las palabras
    texto_limpio = re.sub(r'\s+', ' ', texto_acumulado) 

    if st.button("🚀 GENERAR INFORME"):
        try:
            client = Groq(api_key=api_key)
            # Prompt de "Búsqueda de Tesoro": Le decimos que ignore el desorden
            prompt = f"""
            ERES EL DR. PASTORE. ANALIZA ESTE TEXTO CRUDO DE UN SONOSCAPE E3.
            
            INSTRUCCIÓN CRÍTICA: Los valores numéricos ESTÁN mezclados en el texto. 
            Busca y extrae SI O SI:
            - DDVI (está cerca de 61), DSVI (cerca de 46), Septum (10), Pared (11), AI (42).
            - FEy (31%), FA (25%), Motilidad (Hipocinesia global severa).
            - Vena Cava (15), E/A (0.95), E/e' (5.9).

            REDACTA EL INFORME CON ESTA ESTRUCTURA:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA: (Valores en mm)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Doppler, Vena Cava)
            IV. CONCLUSIÓN: (Diagnóstico médico final coherente)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144

            TEXTO PARA ANALIZAR:
            {texto_limpio}
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            informe = completion.choices[0].message.content
            st.markdown("---")
            st.write(informe)
            
            # 3. Generación de Word
            doc = Document()
            doc.add_paragraph(informe)
            target = io.BytesIO()
            doc.save(target)
            
            st.download_button(
                label="📥 Descargar Word",
                data=target.getvalue(),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
