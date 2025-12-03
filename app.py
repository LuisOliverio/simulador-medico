import streamlit as st
import google.generativeai as genai
import PyPDF2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simulador Médico", page_icon="🩺", layout="centered", initial_sidebar_state="expanded")

# --- FUNCION: CONECTAR A GOOGLE SHEETS ---
def guardar_en_db(tema, puntaje, feedback):
    try:
        # Usamos los secretos de Streamlit
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Creamos credenciales desde el secreto
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre la hoja (Asegúrate que se llame EXACTAMENTE igual)
        sheet = client.open("Simulador_DB").sheet1
        
        # Agrega la fila
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([fecha, tema, puntaje, feedback])
        return True
    except Exception as e:
        st.error(f"Error guardando en DB: {e}")
        return False

# --- CSS HACK ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col1, col2 = st.columns([1, 6])
with col1: st.markdown("## 🩺") 
with col2:
    st.markdown("### Práctica Deliberada")
    st.caption("Dr. Luis Oliverio | Medicina Interna")
st.divider()

# --- SETUP LLAVE GEMINI ---
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    api_key = st.text_input("API Key:", type="password")
    if not api_key: st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-flash-latest')

# --- FUNCIONES AUXILIARES ---
def get_pdf_text(pdf_file):
    text = ""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page in pdf_reader.pages: text += page.extract_text()
    return text

# --- SIDEBAR ---
with st.sidebar:
    st.header("📚 Referencia")
    uploaded_file = st.file_uploader("Sube PDF", type="pdf")
    pdf_text = get_pdf_text(uploaded_file) if uploaded_file else ""
    if pdf_text: st.success("Guía leída correctamente")
    
    st.divider()
    if st.button("🔄 Nuevo Paciente"):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()

# --- MEMORIA SESIÓN ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None

# --- LÓGICA PRINCIPAL ---
if st.session_state.chat_session is None:
    tema = st.text_input("Tema clínico:", placeholder="Ej: Cetoacidosis Diabética")
    
    if st.button("⚡ Generar Caso"):
        if not tema: st.error("Escribe un tema.")
        else:
            with st.spinner("Creando paciente..."):
                contexto_extra = ""
                if pdf_text:
                    contexto_extra = f"""
                    DOCUMENTO DE REFERENCIA SUBIDO:
                    {pdf_text[:30000]} ... (truncado si es muy largo)
                    ÚSALO PARA EVALUAR.
                    """

                prompt = f"""
                    Eres un Profesor Senior de Medicina Interna.
                    Genera un caso de {tema}.
                    1. Inicia solo con Motivo de Consulta y Vitales.
                    2. Espera interrogatorio.
                    3. Cuando el usuario diga "DIAGNÓSTICO FINAL" o "TRATAMIENTO FINAL":
                       - Evalúa del 0 al 100.
                       - Empieza tu respuesta con la frase exacta: "CALIFICACIÓN: [numero]/100".
                       - Luego da tu feedback detallado.
                       - Si hay PDF adjunto, cita sus recomendaciones.
                    
                    {contexto_extra}
                """
                chat = model.start_chat(history=[{"role": "user", "parts": [prompt]}])
                response = chat.send_message("Empieza.")
                st.session_state.chat_session = chat
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                # Guardamos el tema en sesión para la DB
                st.session_state.tema_actual = tema
                st.rerun()

else:
    for msg in st.session_state.messages:
        icono = "👨‍⚕️" if msg["role"] == "user" else "📋"
        with st.chat_message(msg["role"], avatar=icono):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Tu conducta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="📋"):
            with st.spinner("Analizando..."):
                response = st.session_state.chat_session.send_message(prompt)
                texto_resp = response.text
                st.markdown(texto_resp)
                st.session_state.messages.append({"role": "assistant", "content": texto_resp})
                
                # --- DETECTOR DE CALIFICACIÓN ---
                # Si la IA nos califica, guardamos en DB
                if "CALIFICACIÓN:" in texto_resp:
                    try:
                        # Extraer numero simple
                        score = texto_resp.split("CALIFICACIÓN:")[1].split("/")[0].strip()
                        # Guardar
                        if guardar_en_db(st.session_state.tema_actual, score, texto_resp[:100]):
                            st.toast("💾 Resultado guardado en tu Historial!", icon="✅")
                    except:
                        pass # Si falla el parseo, no rompemos la app