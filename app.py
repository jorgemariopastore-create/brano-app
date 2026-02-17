
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document

# 1. Configuración básica
st.set_page_config(page_title="CardioReport", layout="centered")

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. Entrada de datos
archivo = st.file_uploader("📂 Subir PDF", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # 3. Lectura directa (Sin funciones complejas que saturen la memoria)
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    texto_sucio = ""
    for pagina in pdf:
        texto_sucio += pagina.get_text() + "\n"
    pdf.close()

    if st.button("🚀 GENERAR INFORME"):
        try:
            client = Groq(api_key=api_key)
            # Un prompt directo, sin vueltas
            prompt = f"""
            Actúa como el Dr. Pastore. Del siguiente texto de un ecógrafo SonoScape E3, 
            extrae los valores (DDVI, DSVI, FEy, etc.) y redacta un informe profesional.
            
            Usa este formato:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA:
            II. FUNCIÓN VENTRICULAR:
            III. EVALUACIÓN HEMODINÁMICA:
            IV. CONCLUSIÓN:
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL PDF:
            {texto_sucio}
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            informe = completion.choices[0].message.content
            st.write(informe)
            
            # 4. Descarga simple
            doc = Document()
            doc.add_paragraph(informe)
            target = io.BytesIO()
            doc.save(target)
            
            st.download_button(
                label="📥 Descargar Word",
                data=target.getvalue(),
                file_name="informe.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
