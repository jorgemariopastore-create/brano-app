
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document

# 1. Interfaz limpia
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del SonoScape E3", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # 2. El método de lectura que rescató los datos de Manuel
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    # TEXT_PRESERVE_WHITESPACE es el secreto para que la IA vea las tablas
    texto_para_ia = ""
    for pagina in pdf:
        texto_para_ia += pagina.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
    pdf.close()

    if st.button("🚀 GENERAR INFORME"):
        try:
            client = Groq(api_key=api_key)
            # Prompt ultra-específico para que no se rinda
            prompt = f"""
            ERES EL DR. PASTORE. USA ESTE TEXTO DE UN ECOGRAFO SONOSCAPE E3.
            LOS DATOS ESTÁN AHÍ (Busca DDVI 61, FEy 31%, Hipocinesia, etc). 
            NO digas "No se proporcionan detalles". Si ves el número, úsalo.

            FORMATO:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA: (Valores mm)
            II. FUNCIÓN VENTRICULAR: (FEy, Motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Doppler)
            IV. CONCLUSIÓN: (Resumen médico)
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144

            TEXTO DEL PDF:
            {texto_para_ia}
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            informe = completion.choices[0].message.content
            st.markdown("---")
            st.write(informe)
            
            # 3. Generación de Word inmediata
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
            st.error(f"Error de conexión: {e}")
