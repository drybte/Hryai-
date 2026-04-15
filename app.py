import os
import sqlite3
import requests
import datetime
import urllib3
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

app = Flask(__name__)

# --- KONFIGURACE DATABÁZE (podle obrázku) ---
DB_PATH = "/data/history.db"

def get_db_connection():
    # Vytvoří složku /data, pokud neexistuje (pro lokální testování)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Inicializace tabulky pro historii
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS history 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         genre TEXT, 
         recommendation TEXT, 
         timestamp TEXT)
    ''')
    conn.commit()
    conn.close()

init_db()

api_key = os.environ.get("OPENAI_API_KEY", "")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# Nový endpoint pro zobrazení historie
@app.route('/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM history ORDER BY id DESC').fetchall()
    conn.close()
    
    # Převedeme na seznam slovníků pro snadné zobrazení
    history_list = [dict(row) for row in rows]
    return jsonify(history_list)

@app.route('/recommend', methods=['POST'])
def game_advisor():
    data = request.json
    genre = data.get("genre", "akční")
    
    prompt = (
        f"Uživatel má rád herní žánr: {genre}. "
        "Doporuč mu jednu konkrétní aktuální hru, která do tohoto žánru patří. "
        "Odpověz pouze jednou krátkou větou v češtině a stručně uveď, proč by si ji měl zahrát."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gemma3:27b", 
        "messages": [
            {"role": "system", "content": "Jsi expert na videohry a herní průmysl."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=20, 
            verify=False
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            
            # --- ULOŽENÍ DO DATABÁZE ---
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO history (genre, recommendation, timestamp) VALUES (?, ?, ?)',
                (genre, ai_response, datetime.datetime.now().strftime("%d.%m. %H:%M"))
            )
            conn.commit()
            conn.close()
            # ---------------------------

            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({"error": f"Server vrátil {response.status_code}."}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
