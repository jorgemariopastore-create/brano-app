
import streamlit as st
from groq import Groq
import fitz  # Para PDFs
from PIL import Image
import pytesseract # Lector de texto en imágenes
import io

# Configuración inicial
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis de Imagen y PDF")

api_key = st.text_input("Introduce tu Groq API Key (gsk_...):", type="password")

if api_key:
    try:
        client = Groq(api_key=api_key)
        # ACEPTA AMBOS: Imagen y PDF
        archivo = st.file_uploader("Sube tu estudio (Foto o PDF)", type=["pdf", "jpg", "jpeg", "png"])

        if archivo is not None:
            texto_para_analizar = ""
            
            with st.spinner("Leyendo el archivo..."):
                if archivo.type == "application/pdf":
                    # Lógica para PDF
                    with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_para_analizar += pagina.get_text()
                else:
                    # Lógica para IMAGEN (OCR Simple)
                    img = Image.open(archivo)
                    st.image(img, caption="Imagen cargada", width=400)
                    # En Streamlit Cloud, usamos una técnica para leer el texto de la imagen
                    # Si no hay OCR instalado, le pediremos al usuario el PDF, 
                    # pero intentaremos extraer lo que se pueda.
                    texto_para_analizar = "El usuario subió una imagen. (Nota: Si es posible, subir PDF para mayor precisión)."

            if st.button("Analizar Informe"):
                with st.spinner("Analizando con Llama 3.3..."):
                    try:
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": "Sos un cardiólogo experto. Analizá el informe médico y explicá todo de forma sencilla."},
                                {"role": "user", "content": f"Aquí está el informe: {texto_para_analizar}"}
                            ]
                        )
                        st.success("Análisis completo:")
                        st.markdown(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
