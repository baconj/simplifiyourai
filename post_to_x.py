import tweepy
import random
from googleapiclient.discovery import build
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for

# Load environment variables
load_dotenv()
project_root = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_root, "bot.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# X API setup
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
client = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN,
                       access_token_secret=ACCESS_TOKEN_SECRET)

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Flask app
app = Flask(__name__)
scheduled_posts = []


def get_trending_topics(niche):
    """Fetch 5 'trending' topics by searching recent niche-related tweets and extracting common keywords."""
    try:
        # Search recent tweets for the niche
        query = f"{niche} -filter:retweets lang:en"
        response = client.search_recent_tweets(query=query, max_results=50, tweet_fields=["text"])
        if not response.data:
            return ["No trends found"]

        # Simple keyword extraction (top words from tweets)
        from collections import Counter
        words = []
        for tweet in response.data:
            words.extend([word.lower() for word in tweet.text.split() if len(word) > 4 and word.isalpha()])
        common_words = [word for word, count in Counter(words).most_common(5)]
        return common_words if common_words else ["No trends found"]
    except Exception as e:
        logging.error(f"Error fetching trends: {e}")
        return ["Error fetching trends"]


def get_tweets_for_trends(niche, trends):
    """Fetch 5 tweets related to the niche and trends."""
    tweets = []
    try:
        for trend in trends[:5]:  # Limit to 5
            query = f"{niche} {trend} -filter:retweets lang:en"
            response = client.search_recent_tweets(query=query, max_results=1, tweet_fields=["text"])
            if response.data:
                tweet_text = response.data[0].text
                if len(tweet_text) > 140:  # Truncate if too long
                    tweet_text = tweet_text[:137] + "..."
                tweets.append(tweet_text)
            else:
                tweets.append(f"No tweet found for {trend}")
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")
        tweets.append("Error fetching tweet")
    return tweets[:5]  # Ensure max 5


def get_youtube_video_options(query):
    """Fetch 3 YouTube video options for a query."""
    try:
        request = youtube.search().list(part="snippet", maxResults=3, q=query + " tutorial -inurl:(live stream)",
                                        type="video", videoDuration="short")
        response = request.execute()
        return [{"url": f"https://youtu.be/{v['id']['videoId']}", "title": v["snippet"]["title"],
                 "thumbnail": v["snippet"]["thumbnails"]["default"]["url"]} for v in response["items"]]
    except Exception as e:
        logging.error(f"Error fetching videos: {e}")
        return []


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        niche = request.form.get('niche', '').strip()
        if niche:
            # Get trends and tweets
            trends = get_trending_topics(niche)
            tweets = get_tweets_for_trends(niche, trends)
            # Pair each tweet with 3 video options
            tweet_video_pairs = []
            for tweet in tweets:
                videos = get_youtube_video_options(f"{niche} {tweet}")
                tweet_video_pairs.append({"tweet": tweet, "videos": videos})
            return render_template('index.html', pairs=tweet_video_pairs, scheduled=scheduled_posts, niche=niche)
    return render_template('index.html', pairs=None, scheduled=scheduled_posts, niche="")


@app.route('/schedule', methods=['POST'])
def schedule():
    tweet = request.form['tweet']
    video_url = request.form['video']
    post_time = datetime.utcnow() + timedelta(hours=len(scheduled_posts) * random.uniform(7, 9))
    message = f"{tweet} Learn more: {video_url}" if video_url else tweet
    if len(message) > 280:
        message = message[:277] + "..."
    scheduled_posts.append({"text": message, "time": post_time.strftime("%Y-%m-%d %H:%M UTC")})
    try:
        client.create_tweet(text=message, execute_at=int(post_time.timestamp()))
        logging.info(f"Scheduled: {message}")
    except Exception as e:
        logging.error(f"Error: {e}")
    return redirect(url_for('home'))


if __name__ == "__main__":
    print("Starting web interface at http://127.0.0.1:5000")
    app.run(debug=True)