import streamlit as st
import google.generativeai as genai
import PyPDF2

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Simulador Médico", 
    page_icon="🩺", 
    layout="centered", 
    initial_sidebar_state="expanded"  # <--- ESTO FUERZA QUE SIEMPRE SE MUESTRE
)
# --- CSS HACK: LIMPIEZA VISUAL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display:none;}
            .block-container {padding-top: 2rem; padding-bottom: 2rem;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- HEADER ---
col1, col2 = st.columns([1, 6])
with col1:
    st.markdown("## 🩺") 
with col2:
    st.markdown("### Práctica Deliberada")
    st.caption("Dr. Luis Oliverio | Medicina Interna")
st.divider()

# --- GESTIÓN DE LA LLAVE ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("API Key:", type="password")

if not api_key:
    st.info("👈 Configura tu API Key.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-flash-latest') # Usamos Flash porque acepta muchos tokens (PDFs largos)

# --- FUNCIÓN PARA LEER PDF ---
def get_pdf_text(pdf_file):
    text = ""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# --- BARRA LATERAL (EL BIBLIOTECARIO) ---
with st.sidebar:
    st.header("📚 Referencia Bibliográfica")
    uploaded_file = st.file_uploader("Sube tu Guía/Artículo (PDF)", type="pdf")
    
    pdf_text = ""
    if uploaded_file is not None:
        with st.spinner("Leyendo documento..."):
            pdf_text = get_pdf_text(uploaded_file)
            st.success(f"Guía cargada: {len(pdf_text)} caracteres")
    
    st.divider()
    if st.button("🔄 Nuevo Paciente"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()

# --- MEMORIA ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- LÓGICA DEL SIMULADOR ---
if st.session_state.chat_session is None:
    # FASE 1: SETUP
    st.info("Configura el caso. Si subiste un PDF, la evaluación se basará en él.")
    
    tema = st.text_input("Tema clínico:", placeholder="Ej: Neumonía adquirida en la comunidad")
    
    if st.button("⚡ Generar Caso"):
        if not tema:
            st.error("Escribe un tema.")
        else:
            with st.spinner("Analizando guías y generando paciente..."):
                
                # INSTRUCCIÓN MAESTRA (PROMPT RAG)
                contexto_extra = ""
                if pdf_text:
                    contexto_extra = f"""
                    --------------------------------------------------
                    ⚠️ INSTRUCCIÓN DE REFERENCIA (RAG):
                    El usuario ha subido un documento oficial de referencia.
                    Aquí está el contenido del documento:
                    {pdf_text}
                    
                    REGLA DE ORO:
                    Al final de la simulación, cuando evalúes al usuario, DEBES comparar sus decisiones
                    CONTRA este texto específico. Si la guía dice "X" y el usuario hizo "Y", márcalo como error.
                    Cita partes del texto en tu feedback final.
                    --------------------------------------------------
                    """

                prompt_sistema = f"""
                    Actúa como un profesor estricto de Medicina Interna.
                    Genera un caso de {tema}.
                    
                    {contexto_extra}
                    
                    1. Empieza SOLO con el Motivo de Consulta y Signos Vitales.
                    2. Espera preguntas.
                    3. Cuando el usuario diga "Diagnóstico Final" o de un tratamiento definitivo, EVALÚA su desempeño (0-100).
                    4. Justifica la nota basándote en la evidencia proporcionada (si la hay) o en guías internacionales estándar.
                """
                
                chat = model.start_chat(history=[{"role": "user", "parts": [prompt_sistema]}])
                response = chat.send_message("Empieza la simulación.")
                
                st.session_state.chat_session = chat
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

else:
    # FASE 2: CHAT
    for msg in st.session_state.messages:
        icono = "👨‍⚕️" if msg["role"] == "user" else "📋"
        with st.chat_message(msg["role"], avatar=icono):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Tu conducta médica..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="📋"):
            with st.spinner("Consultando evidencia..."):
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})