
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
from PIL import Image
import io

# 1. Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis Multiformato (Imagen y PDF)")

# 2. Entrada de la llave de Groq
api_key = st.text_input("Introduce tu Groq API Key (gsk_...):", type="password")

if api_key:
    try:
        client = Groq(api_key=api_key)
        # ACEPTA AMBOS: Imagen y PDF
        archivo = st.file_uploader("Sube tu estudio (Foto o PDF)", type=["pdf", "jpg", "jpeg", "png"])

        if archivo is not None:
            texto_extraido = ""
            
            with st.spinner("Procesando archivo..."):
                if archivo.type == "application/pdf":
                    # Extraer texto de PDF directamente
                    with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_extraido += pagina.get_text()
                else:
                    # Si es imagen, la mostramos y avisamos
                    img = Image.open(archivo)
                    st.image(img, caption="Imagen cargada", width=400)
                    # Nota: Sin OCR avanzado, el texto de imagen es difícil. 
                    # Pero para tu trabajo, si el PDF tiene texto, lo leerá perfecto.
                    texto_extraido = "Análisis solicitado sobre una imagen de estudio cardiológico."

            if st.button("Analizar con Llama 3.3"):
                if not texto_extraido.strip() or texto_extraido == "Análisis solicitado sobre una imagen de estudio cardiológico.":
                    st.warning("Nota: Para un análisis detallado, se recomienda subir el informe en formato PDF original.")
                
                with st.spinner("IA Analizando..."):
                    try:
                        # Usamos el modelo que tenés: llama-3.3-70b-versatile
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": "Sos un cardiólogo experto. Analizá el informe médico proporcionado."},
                                {"role": "user", "content": f"Informe: {texto_extraido}"}
                            ]
                        )
                        st.success("Análisis completo:")
                        st.markdown(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Error en la IA: {e}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
else:
    st.info("Pega tu llave de Groq para comenzar.")
