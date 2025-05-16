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
bekannte_coins = {'dogecoin', 'pepe', 'shiba', 'floki', 'wojak', 'babydoge'}
last_alerted = set()

def finde_neue_memecoins(max_results=10):
    query = "#crypto OR #memecoin lang:en -is:retweet"
    tweets = client.search_recent_tweets(query=query, tweet_fields=['entities'], max_results=max_results)
    neue_coins = set()
    if tweets.data:
        for tweet in tweets.data:
            hashtags = tweet.entities.get('hashtags', [])
            for tag in hashtags:
                text = tag['tag'].lower()
                if text not in bekannte_coins and re.match(r'^[a-zA-Z0-9]{3,15}$', text):
                    neue_coins.add(text)
    return list(neue_coins)

def coin_engagement(coin, max_results=20):
    query = f"#{coin} lang:en -is:retweet"
    tweets = client.search_recent_tweets(query=query, tweet_fields=['public_metrics'], max_results=max_results)
    total_likes, total_retweets, total_tweets = 0, 0, 0
    if tweets.data:
        for tweet in tweets.data:
            metrics = tweet.public_metrics
            total_likes += metrics['like_count']
            total_retweets += metrics['retweet_count']
            total_tweets += 1
    return {
        'coin': coin,
        'tweets': total_tweets,
        'likes': total_likes,
        'retweets': total_retweets,
        'engagement': total_likes + total_retweets
    }

def analyse_meme_hype():
    neue_coins = finde_neue_memecoins()
    daten = [coin_engagement(coin) for coin in neue_coins]
    df = pd.DataFrame(daten)
    df = df[df['tweets'] > 2]
    df = df.sort_values(by='engagement', ascending=False)
    return df

def alert_top_coins(df):
    global last_alerted
    top_coins = df[df['engagement'] > 50]
    for _, row in top_coins.iterrows():
        coin = row['coin']
        if coin not in last_alerted:
            twitter_link = f"https://twitter.com/search?q=%23{urllib.parse.quote(coin)}&src=typed_query"
            dextools_link = f"https://www.dextools.io/app/en/ether/pair-explorer?q={urllib.parse.quote(coin)}"
            msg = (
                f"**Hype-Alarm:** #{coin}\n"
                f"Engagement: {row['engagement']}\n"
                f"Tweets: {row['tweets']}\n\n"
                f"[Twitter]({twitter_link}) | [DEXTools]({dextools_link})"
            )
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode='Markdown')
            last_alerted.add(coin)

@app.route('/')
def dashboard():
    df = analyse_meme_hype()
    alert_top_coins(df)

    def twitter_link(coin):
        return f"https://twitter.com/search?q=%23{urllib.parse.quote(coin)}&src=typed_query"

    def dextools_link(coin):
        return f"https://www.dextools.io/app/en/ether/pair-explorer?q={urllib.parse.quote(coin)}"

    def swap_link(coin):
        return f"https://app.uniswap.org/#/swap?outputCurrency={urllib.parse.quote(coin)}"

    df['Twitter'] = df['coin'].apply(lambda c: f"<a href='{twitter_link(c)}' target='_blank'>Twitter</a>")
    df['DEXTools'] = df['coin'].apply(lambda c: f"<a href='{dextools_link(c)}' target='_blank'>DEX</a>")
    df['Buy'] = df['coin'].apply(lambda c: f"<a href='{swap_link(c)}' target='_blank'>Wallet-Link</a>")

    df = df[['coin', 'tweets', 'likes', 'retweets', 'engagement', 'Twitter', 'DEXTools', 'Buy']]

    table_html = df.to_html(escape=False, index=False)
    html = f"""
    <html>
    <head>
        <title>MemeCoin Dashboard</title>
        <meta http-equiv="refresh" content="300">
    </head>
    <body>
        <h1>MemeCoin Hype Dashboard</h1>
        <p>Automatische Aktualisierung alle 5 Minuten</p>
        {table_html}
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
