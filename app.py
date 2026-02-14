
prompt = f"""
Actúa como un médico cardiólogo clínico. Extrae los datos ÚNICAMENTE del texto provisto.
DATOS DEL ESTUDIO ACTUAL: {texto_limpio}

INSTRUCCIONES OBLIGATORIAS:
1. Identifica al paciente y extrae sus valores específicos: DDVI, DSVI, Masa, e Índice de Masa.
2. LOCALIZA LA FRACCIÓN DE EYECCIÓN (FEy) real del texto. 
3. SI la FEy es > 55%, reporta "Función sistólica conservada". 
4. SI la FEy es < 40%, reporta "Deterioro severo" y busca signos de hipocinesia.
5. NO uses datos de ejemplos anteriores. Cíñete al texto de este paciente.

ESTRUCTURA:
DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
I. EVALUACIÓN ANATÓMICA: Reporta diámetros reales encontrados.
II. FUNCIÓN VENTRICULAR: Menciona la FEy real y la técnica usada.
III. EVALUACIÓN HEMODINÁMICA: Detallar Onda E/A y Doppler Tisular.
IV. CONCLUSIÓN: Escribe el diagnóstico técnico basado estrictamente en los números de este estudio.

Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
"""
