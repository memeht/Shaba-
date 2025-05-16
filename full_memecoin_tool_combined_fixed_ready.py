
from flask import Flask
import threading
import time
import os
import requests

app = Flask(__name__)

# Beispiel-Token und Chat-ID (bitte durch echte Werte ersetzen)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Globale Variable, um zu erkennen, ob Coins gefunden wurden
latest_scan_had_results = False

@app.route("/")
def index():
    return "Memecoin Dashboard läuft!"

def sende_telegram_nachricht(text):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print("Telegram-Fehler:", e)

def suche_memecoins():
    global latest_scan_had_results
    while True:
        print("Scanne nach Coins...")
        # Dummy-Simulation
        coins_gefunden = False  # <- Simulation für Testfall "keine Coins gefunden"
        latest_scan_had_results = coins_gefunden
        if coins_gefunden:
            sende_telegram_nachricht("Neue Coins gefunden!")
        time.sleep(600)

def sende_leerstatus():
    global latest_scan_had_results
    while True:
        time.sleep(600)
        if not latest_scan_had_results:
            sende_telegram_nachricht("Noch keine neuen Coins gefunden.")
        latest_scan_had_results = False

# Starte Threads beim App-Start
def starter_threading():
    threading.Thread(target=suche_memecoins, daemon=True).start()
    threading.Thread(target=sende_leerstatus, daemon=True).start()

starter_threading()
