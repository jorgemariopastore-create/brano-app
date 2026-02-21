
def redactar_informe_ia(datos_dict):
    """Groq redacta el texto médico puro sin recomendaciones con manejo de errores"""
    
    # 1. Validación de seguridad: Si no hay datos, no llamamos a la IA
    if not datos_dict:
        return "Error: No se detectaron datos en el archivo subido."

    # Convertimos los datos a texto
    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items()])
    
    prompt = f"""
    Actúa como un cardiólogo profesional redactando los 'Hallazgos' de un ecocardiograma. 
    Usa estos datos técnicos: 
    {datos_texto}
    
    REGLAS ESTRICTAS:
    - NO incluyas recomendaciones ni pasos a seguir.
    - NO des consejos de salud.
    - Usa lenguaje médico formal y técnico.
    - Si el médico escribió 'Observaciones', incorpóralas al texto.
    - Sé directo, empieza con la descripción del estudio.
    """
    
    try:
        # Intentamos con un modelo versátil y actualizado
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Cambiado por uno más reciente y estable
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, 
        )
        return completion.choices[0].message.content
    except Exception as e:
        # Si falla el modelo anterior, intentamos con el 8b (más ligero)
        try:
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return completion.choices[0].message.content
        except Exception as e_inner:
            return f"Error en Groq: {str(e_inner)}. Por favor, verifique la configuración de su API o el formato del Excel."
