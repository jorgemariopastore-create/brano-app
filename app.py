
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document

st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI")

# --- CLAVE API ---
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

if not api_key:
    st.warning("⚠️ Por favor, ingresa la API KEY para continuar.")
    st.stop()

client = Groq(api_key=api_key)
archivos = st.file_uploader("Subir PDF", type=["pdf", "jpg", "png"], accept_multiple_files=True)

if archivos:
    if st.button("GENERAR INFORME AHORA"):
        try:
            with st.spinner("Procesando..."):
                texto_total = ""
                for a in archivos:
                    if a.type == "application/pdf":
                        with fitz.open(stream=a.read(), filetype="pdf") as d:
                            for pag in d:
                                texto_total += pag.get_text()
                    else:
                        texto_total += " (Imagen cargada) "

                # El Prompt que ya sabemos que funciona bien
                prompt = f"Actúa como cardiólogo. Extrae datos de: {texto_total[:5000]}. Reporta DDVI, FEy y Conclusión técnica. Firma: Dr. FRANCISCO ALBERTO PASTORE."
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = completion.choices[0].message.content
                st.success("✅ Informe generado con éxito")
                st.markdown(resultado)
                
                # Crear Word simple
                doc = Document()
                doc.add_heading('INFORME CARDIOLÓGICO', 0)
                doc.add_paragraph(resultado)
                buffer = io.BytesIO()
                doc.save(buffer)
                
                st.download_button("📥 Descargar Word", buffer.getvalue(), "Informe.docx")
        
        except Exception as e:
            st.error(f"Ocurrió un error técnico: {e}")
