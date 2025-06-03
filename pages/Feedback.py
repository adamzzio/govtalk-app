import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# Fungsi buka koneksi DB baru tiap kali dipanggil (tanpa caching koneksi)
def get_db_connection():
    return psycopg2.connect(st.secrets["uri"], cursor_factory=RealDictCursor)

# Ambil daftar nama pemerintah dengan caching data (bukan koneksi)
@st.cache_data(ttl=3600)
def get_gov_names():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT full_name FROM government ORDER BY full_name")
            result = cur.fetchall()
            return [row['full_name'] for row in result]

gov_names = get_gov_names()

st.title("Form Feedback Kebijakan Pemerintah")

with st.form("feedback_form"):
    gov_name = st.selectbox("Nama Pemerintah", gov_names)
    feedback = st.text_area("Masukkan Feedback Anda")
    star_rating = st.feedback("stars")
    submitted = st.form_submit_button("Kirim Feedback")

if submitted:
    if not feedback.strip():
        st.error("Feedback tidak boleh kosong.")
    elif star_rating is None:
        st.error("Mohon berikan rating bintang.")
    else:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                    INSERT INTO feedback (gov_name, feedback, star_rating)
                    VALUES (%s, %s, %s)
                    """
                    cur.execute(sql, (gov_name, feedback, star_rating + 1))
                    conn.commit()
            st.success("Feedback berhasil ditambahkan dan akan ditinjau. Terima kasih atas partisipasi Anda!")
        except Exception as e:
            st.error(f"Gagal mengirim feedback: {e}")
