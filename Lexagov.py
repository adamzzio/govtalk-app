import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

st.set_page_config(page_title="LexaGov", layout="centered")
st.title("LexaGov - Ask Your Government Now")

st.warning(
    "⚠️ Perhatian: Ini adalah prototipe chatbot menggunakan model LLM dengan parameter rendah (Flan-T5-base). "
    "Hasil jawaban mungkin kurang sempurna dan bersifat indikatif saja. "
    "Pemilihan model ini didasarkan pada keterbatasan komputasi dan hardware."
)

st.markdown("---")

@st.cache_resource(ttl=3600)
def init_db():
    return psycopg2.connect(st.secrets["uri"], cursor_factory=RealDictCursor)

conn = init_db()

def get_government_list():
    with conn.cursor() as cur:
        cur.execute("SELECT id, full_name FROM government ORDER BY full_name")
        return cur.fetchall()

government_list = get_government_list()
government_map = {gov['full_name']: gov['id'] for gov in government_list}

selected_gov_name = st.selectbox("Pilih Nama Pejabat:", options=["-- Pilih Pejabat --"] + list(government_map.keys()))

def get_policy_titles(gov_id):
    with conn.cursor() as cur:
        cur.execute("SELECT title FROM policy WHERE gov_id = %s ORDER BY created_at DESC", (gov_id,))
        rows = cur.fetchall()
        return [r['title'] for r in rows]

def get_policy_content(gov_id, title):
    with conn.cursor() as cur:
        cur.execute("SELECT content FROM policy WHERE gov_id = %s AND title = %s", (gov_id, title))
        res = cur.fetchone()
        return res["content"] if res else None

@st.cache_resource
def load_llm():
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")
    return pipeline("text2text-generation", model=model, tokenizer=tokenizer)

llm = load_llm()

if selected_gov_name != "-- Pilih Pejabat --":
    gov_id = government_map[selected_gov_name]
    policy_titles = get_policy_titles(gov_id)

    if not policy_titles:
        st.warning("Tidak ditemukan kebijakan untuk pejabat ini.")
    else:
        selected_policy_title = st.selectbox("Pilih Judul Kebijakan:", options=["-- Pilih Kebijakan --"] + policy_titles)
        if selected_policy_title != "-- Pilih Kebijakan --":
            policy_content = get_policy_content(gov_id, selected_policy_title)
            if policy_content is None:
                st.error("Gagal mengambil isi kebijakan.")
            else:
                st.markdown("### Kebijakan Terpilih:")
                st.write(policy_content[:1000] + ("..." if len(policy_content) > 1000 else ""))

                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                if prompt := st.chat_input("Tanyakan tentang kebijakan ini..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    system_prompt = f"""
Anda adalah asisten AI yang memberikan informasi tentang kebijakan berikut:

{policy_content}

Jawablah pertanyaan berikut secara jelas dan ringkas:

Pertanyaan: {prompt}
""".strip()

                    with st.spinner("🧠 AI menganalisis..."):
                        result = llm(system_prompt, max_new_tokens=2000)[0]["generated_text"]

                    with st.chat_message("assistant"):
                        st.markdown(result)

                    st.session_state.messages.append({"role": "assistant", "content": result})
else:
    st.info("Silakan pilih nama pejabat terlebih dahulu.")
