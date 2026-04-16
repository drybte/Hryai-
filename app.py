import os  # Importuje modul pro praci s operacnim systemem
import requests  # Knihovna pro odesilani HTTP pozadavku na externi API
import datetime  # Modul pro praci s datem a casem
import urllib3  # Modul pro nizkourovnovou HTTP komunikaci
import psycopg2  # Knihovna pro praci s PostgreSQL
from psycopg2.extras import RealDictCursor  # Vraci radky jako slovnik
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Vypne varovani ohledne nezabezpecenych HTTPS pozadavku
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

app = Flask(__name__)

# --- KONFIGURACE DATABAZE ---
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/history_db"
)

def get_db_connection():
    # Vytvori spojeni s PostgreSQL databazi
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Vytvori tabulku history, pokud jeste neexistuje
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            genre TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# Nacte API klic a URL adresu ze systemovych promennych
api_key = os.environ.get("OPENAI_API_KEY", "")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

# --- ROUTY (Webove adresy) ---

@app.route('/', methods=['GET'])
def home():
    # Zobrazi uvodni stranku index.html ze slozky templates
    return render_template('index.html')

@app.route('/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    cur = conn.cursor()

    # Vybere vsechny zaznamy od nejnovejsiho po nejstarsi
    cur.execute("SELECT * FROM history ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(rows)

@app.route('/recommend', methods=['POST'])
def game_advisor():
    data = request.json
    genre = data.get("genre", "akcni")

    # Textovy prikaz, ktery posilame AI modelu
    prompt = (
        f"Uzivatel ma rad herni zanr: {genre}. "
        "Doporuc mu jednu konkretni aktualni hru, ktera do tohoto zanru patri. "
        "Odpovez pouze jednou kratkou vetou v cestine a strucne uved, proc by si ji mel zahrat."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Konfigurace pozadavku pro AI model
    payload = {
        "model": "gemma3:27b",
        "messages": [
            {"role": "system", "content": "Jsi expert na videohry a herni prumysl."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"

        # Odeslani dotazu na AI server
        response = requests.post(
            target_url,
            headers=headers,
            json=payload,
            timeout=20,
            verify=False
        )

        if response.status_code == 200:
            # Vytahne text odpovedi z JSON struktury od AI
            ai_response = response.json()['choices'][0]['message']['content']

            # --- ULOZENI DO DATABAZE ---
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO history (genre, recommendation, timestamp) VALUES (%s, %s, %s)",
                (genre, ai_response, datetime.datetime.now().strftime("%d.%m. %H:%M"))
            )

            conn.commit()
            cur.close()
            conn.close()
            # ---------------------------

            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({"error": f"Server vratil {response.status_code}."}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojeni selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
