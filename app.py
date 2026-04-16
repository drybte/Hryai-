import os  # Importuje modul pro praci s operacnim systemem (napr. cesty k souborum)
import sqlite3  # Importuje knihovnu pro praci s lokalni SQL databazi
import requests  # Knihovna pro odesilani HTTP pozadavku na externi API
import datetime  # Modul pro praci s datem a casem (ulozeni historie)
import urllib3  # Modul pro nizkourovnovou HTTP komunikaci
from flask import Flask, request, jsonify, render_template  # Zakladni webovy framework
from dotenv import load_dotenv  # Nacte promenne prostredi ze souboru .env

# Vypne varovani ohledne nezabezpecenych HTTPS pozadavku (kvuli skolnimu API)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()  # Aktivuje nacitani promennych prostredi

app = Flask(__name__)  # Vytvori instanci Flask aplikace

# --- KONFIGURACE DATABAZE ---
DB_PATH = "/data/history.db"  # Cesta, kam se ulozi soubor s historii v kontejneru

def get_db_connection():
    # Vytvori slozku /data, pokud jeste neexistuje
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)  # Otevre spojeni k databazi
    conn.row_factory = sqlite3.Row  # Umoznuje pristupovat k vysledkum jako ke slovniku
    return conn  # Vrati objekt spojeni

def init_db():
    conn = get_db_connection()  # Pripoji se k databazi
    # Vytvori tabulku history, pokud v souboru jeste neni
    conn.execute('''
        CREATE TABLE IF NOT EXISTS history 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         genre TEXT, 
         recommendation TEXT, 
         timestamp TEXT)
    ''')
    conn.commit()  # Potvrdi zmeny v databazi
    conn.close()  # Uzavre spojeni

init_db()  # Zavola inicializaci hned po spusteni skriptu

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
    conn = get_db_connection()  # Pripoji se k DB
    # Vybere vsechny zaznamy od nejnovejsiho po nejstarsi
    rows = conn.execute('SELECT * FROM history ORDER BY id DESC').fetchall()
    conn.close()
    
    # Prevede data na seznam slovniku pro JavaScript (format JSON)
    history_list = [dict(row) for row in rows]
    return jsonify(history_list)

@app.route('/recommend', methods=['POST'])
def game_advisor():
    data = request.json  # Ziska data odeslana z frontendu (zanr)
    genre = data.get("genre", "akcni")  # Vychozi hodnota je "akcni"
    
    # Textovy prikaz, ktery posilame AI modelu
    prompt = (
        f"Uzivatel ma rad herni zanr: {genre}. "
        "Doporuc mu jednu konkretni aktualni hru, ktera do tohoto zanru patri. "
        "Odpovez pouze jednou kratkou vetou v cestine a strucne uved, proc by si ji mel zahrat."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",  # Autorizacni hlavicka s klicem
        "Content-Type": "application/json"
    }

    # Konfigurace pozadavku pro AI model
    payload = {
        "model": "gemma3:27b",  # Specifikace pouziteho modelu
        "messages": [
            {"role": "system", "content": "Jsi expert na videohry a herni prumysl."},
            {"role": "user", "content": prompt}
        ],
        "stream": False  # Nechceme postupny proud textu, ale celou odpoved naraz
    }

    try:
        clean_url = base_url.rstrip('/')  # Odstrani lomitko na konci URL, pokud tam je
        target_url = f"{clean_url}/chat/completions"  # Cilova adresa API
        
        # Odeslani dotazu na AI server
        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=20,  # Casovy limit pro odpoved (20 sekund)
            verify=False  # Ignoruje kontrolu SSL (potrebne pro skolni proxy)
        )
        
        if response.status_code == 200:
            # Vytahne text odpovedi z JSON struktury od AI
            ai_response = response.json()['choices'][0]['message']['content']
            
            # --- ULOZENI DO DATABAZE ---
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO history (genre, recommendation, timestamp) VALUES (?, ?, ?)',
                (genre, ai_response, datetime.datetime.now().strftime("%d.%m. %H:%M"))
            )
            conn.commit()
            conn.close()
            # ---------------------------

            return jsonify({"recommendation": ai_response})  # Vrati vysledek webu
        else:
            # Vrati chybu, pokud AI server neodpovida spravne
            return jsonify({"error": f"Server vratil {response.status_code}."}), response.status_code

    except Exception as e:
        # Zachyti chyby jako vypadek site nebo pad serveru
        return jsonify({"error": f"Spojeni selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    # Nacte port z prostredi (napr. pro Docker) nebo pouzije vychozi 5000
    port = int(os.environ.get("PORT", 5000))
    # Spusti aplikaci na adrese 0.0.0.0 (dostupna v siti)
    app.run(host="0.0.0.0", port=port)
