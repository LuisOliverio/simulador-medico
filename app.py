import streamlit as st
import google.generativeai as genai

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Simulador Médico", page_icon="🩺", layout="centered")
import streamlit as st
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simulador Médico", page_icon="🩺", layout="centered")

# --- CSS HACK: LIMPIEZA VISUAL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            
            /* Ajuste para que el título no tenga tanto espacio arriba */
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- HEADER PERSONALIZADO (BRANDING) ---
# En lugar de un título simple, usamos columnas para darle estructura
col1, col2 = st.columns([1, 6])

with col1:
    # Aquí podrías poner una imagen con st.image("logo.png") si la subes
    st.markdown("## 🩺") 

with col2:
    st.markdown("### Práctica Deliberada")
    st.caption("Dr. Luis Oliverio | Medicina Interna")

st.divider() # Línea divisoria elegante

# --- GESTIÓN DE LA LLAVE (AUTO-LOGIN) ---
api_key = None

# 1. Busca en secretos primero
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # 2. Si no hay secretos, pide manual (para cuando lo subas a la nube después)
    with st.sidebar:
        api_key = st.text_input("API Key:", type="password")

# --- INTERFAZ ---
st.title("🧠 Simulador Clínico de Memodi")

if not api_key:
    st.info("👈 Configura tu API Key para empezar.")
    st.stop() # Detiene la app aquí si no hay llave

# --- CONFIGURAR CEREBRO ---
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro-latest')

# --- MEMORIA DE LA SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- BOTÓN DE REINICIO ---
with st.sidebar:
    if st.button("🔄 Nuevo Paciente"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()

# --- LÓGICA DEL JUEGO ---
if st.session_state.chat_session is None:
    # FASE 1: CONFIGURACIÓN DEL ESCENARIO
    st.markdown("### Configuración de Práctica")
    col1, col2 = st.columns(2)
    with col1:
        area = st.selectbox("Área:", ["Medicina Interna", "Urgencias", "Cardiología", "Neurología"])
    with col2:
        dificultad = st.select_slider("Dificultad:", options=["Estudiante", "Residente", "Especialista"])
    
    tema_libre = st.text_input("Tema específico (Opcional):", placeholder="Ej. Síncope, Cefalea Thunderclap...")
    
    tema_final = tema_libre if tema_libre else f"Caso aleatorio de {area}"

    if st.button("⚡ Generar Caso Clínico"):
        with st.spinner("Diseñando paciente virtual..."):
            prompt_sistema = f"""
                Eres un Simulador de Casos Clínicos nivel {dificultad}.
                Genera un caso de {tema_final}.
                1. Empieza SOLO con el Motivo de Consulta y Signos Vitales.
                2. NO des diagnósticos ni expliques nada aún.
                3. Adopta la personalidad del paciente (responde corto si le duele, o ansioso).
                4. Espera preguntas del doctor.
                5. CRÍTICO: Cuando el usuario diga "DIAGNÓSTICO FINAL: [su diagnostico]", evalúa su desempeño 0-100 y justifica basándote en guías clínicas.
            """
            
            chat = model.start_chat(history=[{"role": "user", "parts": [prompt_sistema]}])
            response = chat.send_message("Empieza la simulación ahora.")
            
            st.session_state.chat_session = chat
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()

else:
    # FASE 2: EL CHAT (QUIRÓFANO)
    for msg in st.session_state.messages:
        # Usamos íconos para diferenciar
        icono = "👨‍⚕️" if msg["role"] == "user" else "🤒"
        with st.chat_message(msg["role"], avatar=icono):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Interroga o da indicaciones..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤒"):
            with st.spinner("Pensando..."):
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})