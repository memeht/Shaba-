
import threading
import time
import requests
from bs4 import BeautifulSoup
import os
from telegram import Bot
from flask import Flask, render_template_string
import urllib.parse

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
latest_scan = {}

def get_new_tokens(limit=5):
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_asc&per_page={}&page=1&sparkline=false".format(limit)
    try:
        res = requests.get(url)
        if res.status_code != 200:
            print("CoinGecko API-Fehler")
            return []
        coins = res.json()
        coin_data = []
        for data in coins:
            if data['name'] and data['id'] and data['market_cap']:
                detail_url = f"https://api.coingecko.com/api/v3/coins/{data['id']}"
                detail_res = requests.get(detail_url)
                if detail_res.status_code == 200:
                    detail = detail_res.json()
                    homepage = detail['links']['homepage'][0] if detail['links']['homepage'] else ""
                    coin_data.append({
                        "name": data["name"],
                        "website": homepage,
                        "contract": detail.get("contract_address", "n/a"),
                        "market_cap": data["market_cap"],
                        "rank": data["market_cap_rank"]
                    })
        return coin_data
    except Exception as e:
        print("Fehler bei CoinGecko:", e)
        return []

def check_website(url):
    score = 0
    details = []

    try:
        start = time.time()
        response = requests.get(url, timeout=10)
        load_time = time.time() - start

        if response.status_code != 200:
            return 0, ["Seite nicht erreichbar"]

        if url.startswith("https://"):
            score += 1
            details.append("✔️ HTTPS aktiv")
        else:
            details.append("⚠️ Kein HTTPS")

        if load_time < 2:
            score += 1
            details.append(f"✔️ Ladezeit: {round(load_time, 2)}s")
        else:
            details.append(f"⚠️ Langsame Ladezeit: {round(load_time, 2)}s")

        soup = BeautifulSoup(response.text, "html.parser")

        keywords = ["whitepaper", "tokenomics", "roadmap", "team", "audit"]
        found = 0
        for word in keywords:
            if word in response.text.lower():
                found += 1
        score += found
        details.append(f"✔️ {found}/5 Schlüsselwörter gefunden")

    except Exception as e:
        return 0, [f"Fehler: {str(e)}"]

    return score, details

def notify_telegram(name, website, contract, market_cap, rank, score, details):
    dex_link = f"https://www.dextools.io/app/en/ether/pair-explorer?q={urllib.parse.quote(contract)}"
    swap_link = f"https://app.uniswap.org/#/swap?outputCurrency={urllib.parse.quote(contract)}"

    msg = f"**Neue MemeCoin-Seite erkannt:**\n"
    msg += f"**Name:** {name}\n"
    msg += f"**Website:** {website}\n"
    msg += f"**Market Cap:** ${market_cap}\n"
    msg += f"**Rank:** #{rank}\n"
    msg += f"**Score:** {score}/10\n"
    msg += "\n".join(details)
    msg += f"\n\n[DEXTools]({dex_link}) | [Swap-Link]({swap_link})"

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode='Markdown')
        print("Telegram gesendet:", name)
    except Exception as e:
        print("Telegram Fehler:", e)

def scan_loop():
    global latest_scan
    print("Starte Hintergrund-Scan...")
    while True:
        for project in get_new_tokens():
            score, details = check_website(project["website"])
            latest_scan[project["name"]] = {
                "score": score,
                "website": project["website"],
                "contract": project["contract"],
                "market_cap": project["market_cap"],
                "rank": project["rank"],
                "details": details
            }
            notify_telegram(project["name"], project["website"], project["contract"], project["market_cap"], project["rank"], score, details)
            time.sleep(2)
        print("Warte 10 Minuten...")
        time.sleep(600)

@app.route('/')
def dashboard():
    if not latest_scan:
        return "<h2>Dashboard ist aktiv, aber es wurden noch keine MemeCoins gefunden.</h2><p>Bitte in ein paar Minuten erneut laden...</p>"

    rows = ""
    for name, info in latest_scan.items():
        dex = f"https://www.dextools.io/app/en/ether/pair-explorer?q={urllib.parse.quote(info['contract'])}"
        swap = f"https://app.uniswap.org/#/swap?outputCurrency={urllib.parse.quote(info['contract'])}"
        rows += f"<tr><td>{name}</td><td>{info['score']}/10</td><td>${info['market_cap']}</td><td>#{info['rank']}</td><td><a href='{info['website']}' target='_blank'>Seite</a></td><td><a href='{dex}' target='_blank'>DEX</a></td><td><a href='{swap}' target='_blank'>Swap</a></td></tr>"

    html = f"""
    <html><head><title>MemeCoin Watcher</title></head>
    <body>
    <h2>Letzte geprüfte MemeCoin-Projekte:</h2>
    <table border='1'>
        <tr><th>Name</th><th>Score</th><th>Market Cap</th><th>Rank</th><th>Website</th><th>DEXTools</th><th>Swap</th></tr>
        {rows}
    </table>
    </body></html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    threading.Thread(target=scan_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
