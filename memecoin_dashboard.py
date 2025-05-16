
from flask import Flask, render_template_string
import tweepy
import pandas as pd
import re
from telegram import Bot
import urllib.parse
import os

# ==== Konfiguration ====
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

client = tweepy.Client(bearer_token=BEARER_TOKEN)
bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)
bekannte_coins = {'dogecoin', 'pepe', 'shiba', 'floki', 'akita'}
last_alerted = set()

def finde_neue_memecoins(max_results=10):
    query = "#crypto OR #memecoin lang:en -is:retweet"
    tweets = client.search_recent_tweets(query=query, max_results=max_results)
    neue_coins = set()
    if tweets.data:
        for tweet in tweets.data:
            matches = re.findall(r'\$\w+', tweet.text)
            for match in matches:
                coin = match.lower().strip('$')
                if coin not in bekannte_coins and coin not in last_alerted:
                    neue_coins.add(coin)
    return neue_coins

def sende_telegram_nachricht(nachricht):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=nachricht)

@app.route('/')
def home():
    return render_template_string("""
    <h1>Memecoin Dashboard läuft!</h1>
    <p>Telegram-Benachrichtigungen sind aktiv.</p>
    """)

if __name__ == '__main__':
    app.run(debug=True)
