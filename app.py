
import streamlit as st
from groq import Groq
import base64
from PIL import Image
import io
import fitz

# 1. Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis de Informes Cardiológicos")

# 2. Entrada de la llave de Groq
api_key = st.text_input("Introduce tu Groq API Key (gsk_...):", type="password")

if api_key:
    try:
        client = Groq(api_key=api_key)
        
        # 3. Subida de archivos
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            # Procesamiento de imagen o PDF
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
            else:
                img_data = archivo.read()
                img = Image.open(io.BytesIO(img_data))

            st.image(img, caption="Estudio cargado", width=500)

            # 4. Botón de análisis
            if st.button("Analizar ahora"):
                with st.spinner("La IA está leyendo el informe..."):
                    try:
                        # Convertir a base64
                        base64_image = base64.b64encode(img_data if archivo.type != "application/pdf" else img_data).decode('utf-8')
                        
                        # USAMOS EL MODELO DE VISIÓN POR DEFECTO ACTUAL
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
                        )
                        st.success("Análisis completado:")
                        st.markdown(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Error técnico: {e}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
else:
    st.info("Pega tu llave de Groq para empezar.")
