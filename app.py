
import streamlit as st
from groq import Groq
import base64
from PIL import Image
import io
import fitz

st.set_page_config(page_title="CardioReport AI (Groq)", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Versión estable para Argentina")

# Entrada de la llave de Groq
api_key = st.text_input("Introduce tu Groq API Key (gsk_...):", type="password")

if api_key:
    try:
        client = Groq(api_key=api_key)
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            # Procesar imagen o PDF
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
            else:
                img_data = archivo.read()
                img = Image.open(io.BytesIO(img_data))

            st.image(img, caption="Estudio cargado", width=400)

            if st.button("Analizar con IA"):
                with st.spinner("Analizando con Llama 3 (Groq)..."):
                    try:
                        # Convertir imagen a base64 para enviarla
                        base64_image = base64.b64encode(img_data if archivo.type != "application/pdf" else img_data).decode('utf-8')
                        
                        completion = client.chat.completions.create(
                            model="llama-3.2-11b-vision-preview",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": "Actúa como un cardiólogo experto. Analiza este informe médico y explica los resultados en lenguaje sencillo para el paciente."},
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                    ]
                                }
                            ],
                            temperature=0.5,
                        )
                        st.success("Análisis completado:")
                        st.markdown(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
else:
    st.info("Obtén tu llave gratis en: https://console.groq.com/keys")
