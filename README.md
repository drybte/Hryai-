 Popis projektu

Tato aplikace slouží k doporučování videoher na základě zvoleného žánru. Uživatel zadá herní žánr a aplikace pomocí AI vygeneruje jedno konkrétní doporučení včetně krátkého vysvětlení.

Aplikace také ukládá historii doporučení do databáze, kterou je možné zobrazit.

---

 Použité technologie

* Flask – backend webová aplikace
* requests – komunikace s externím API
* python-dotenv – načítání proměnných prostředí
* SQLite – ukládání historie
* Docker – kontejnerizace aplikace

---

 Funkce aplikace

* zadání herního žánru
* generování doporučení pomocí AI
* ukládání historie do databáze
* zobrazení historie doporučení

---

 API endpointy

| Endpoint     | Metoda | Popis                     |
| ------------ | ------ | ------------------------- |
| `/`          | GET    | Zobrazí hlavní stránku    |
| `/recommend` | POST   | Vrátí doporučení hry      |
| `/history`   | GET    | Vrátí historii doporučení |

---

 Databáze

Používá se databáze SQLite.

Tabulka `history` obsahuje:

* `id` – unikátní identifikátor
* `genre` – herní žánr
* `recommendation` – doporučená hra
* `timestamp` – čas vytvoření

---

Spuštění pomocí Dockeru

 1. Nastavení proměnných prostředí

Vytvoř `.env` soubor:

```
OPENAI_API_KEY=tvuj_klic
OPENAI_BASE_URL=https://kurim.ithope.eu/v1
```

---

 2. Spuštění aplikace

```
docker-compose up --build
```

---

 3. Otevření aplikace

Aplikace poběží na:

```
http://localhost:8081
```

---

 Jak aplikace funguje

1. Uživatel zadá žánr
2. Backend vytvoří dotaz pro AI
3. Odešle HTTP požadavek na API
4. AI vrátí odpověď
5. Výsledek se uloží do databáze
6. Odpověď se zobrazí uživateli

---

 Bezpečnost

* API klíč není uložen v kódu
* používají se proměnné prostředí (.env)

---
 Shrnutí

Jedná se o jednoduchou webovou aplikaci ve Flasku, která komunikuje s AI přes API, běží v Docker kontejneru a ukládá historii do SQLite databáze.

---
