import os
import time
import datetime
import requests
import urllib3
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Vypne SSL warningy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

app = Flask(__name__)

# -----------------------------
# KONFIGURACE
# -----------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/history_db"
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemma3:27b")


# -----------------------------
# DB FUNKCE
# -----------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def wait_for_db():
    for _ in range(10):
        try:
            conn = get_db_connection()
            conn.close()
            print("DB ready")
            return
        except Exception:
            print("Cekam na DB...")
            time.sleep(2)
    raise Exception("Databaze nenabehla")


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

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


# Inicializace DB
wait_for_db()
init_db()


# -----------------------------
# ROUTY
# -----------------------------
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "API bezi"})


@app.route('/history', methods=['GET'])
def get_history():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM history ORDER BY id DESC")
        rows = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(rows)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        genre = data.get("genre", "akcni")

        prompt = (
            f"Uzivatel ma rad herni zanr: {genre}. "
            "Doporuc jednu konkretni aktualni hru. "
            "Odpovez jednou kratkou vetou v cestine."
        )

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "Jsi expert na videohry."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }

        target_url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"

        response = requests.post(
            target_url,
            headers=headers,
            json=payload,
            timeout=20,
            verify=False
        )

        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        if response.status_code != 200:
            return jsonify({
                "error": "AI server chyba",
                "status": response.status_code,
                "detail": response.text
            }), response.status_code

        ai_response = response.json()['choices'][0]['message']['content']

        # ulozeni do DB
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO history (genre, recommendation, timestamp) VALUES (%s, %s, %s)",
            (genre, ai_response, datetime.datetime.now().strftime("%d.%m. %H:%M"))
        )

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"recommendation": ai_response})

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout AI server"}), 504

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Nelze se pripojit k AI serveru"}), 502

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# START
# -----------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # DULEZITE!
    app.run(host="0.0.0.0", port=port)
