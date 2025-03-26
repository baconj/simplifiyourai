import tweepy
import random
import requests
from googleapiclient.discovery import build
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for

# Load environment variables from .env
load_dotenv()
project_root = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_root, "bot.log")
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# X API setup (Free tier - posting only)
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
client = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# SerpApi setup
SERP_API_KEY = os.getenv("SERP_API_KEY")

app = Flask(__name__)
scheduled_posts = []

def get_trending_topics(niche):
    """Fetch 3 trending topics from SerpApi Google Trends."""
    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_trends",
            "q": niche,
            "data_type": "RELATED_TOPICS",
            "api_key": SERP_API_KEY
        }
        logging.info(f"Fetching trends for niche: {niche}")
        response = requests.get(url, params=params).json()
        topics = [item["topic"]["title"] for item in response.get("related_topics", {}).get("rising", [])[:3]]
        if not topics:
            topics = [item["topic"]["title"] for item in response.get("related_topics", {}).get("top", [])[:3]]
        logging.info(f"Found trends: {topics}")
        return topics if topics else [f"{niche} trend {i}" for i in range(1, 4)]
    except Exception as e:
        logging.error(f"Error fetching trends: {e}")
        return [f"{niche} trend {i}" for i in range(1, 4)]

def generate_x_posts(topic):
    """Simulate Grok generating 3 X posts for a topic."""
    return [
        f"{topic}: Boost your income with this AI trick! #AIhustle",
        f"{topic}: Just made $50 fast—here’s the AI secret. #AIhustle",
        f"{topic}: Why {topic} is the future of side gigs. #AIhustle"
    ]

def get_youtube_video_options(query):
    """Fetch 3 YouTube videos: last 6 months, >100k views, short duration."""
    try:
        # Step 1: Search videos from last 6 months
        six_months_ago = (datetime.now() - timedelta(days=180)).isoformat() + "Z"
        search_request = youtube.search().list(
            part="snippet",
            maxResults=10,  # Fetch extra to filter by views
            q=query + " tutorial -inurl:(live stream)",
            type="video",
            videoDuration="short",
            publishedAfter=six_months_ago
        )
        search_response = search_request.execute()
        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

        if not video_ids:
            logging.info(f"No videos found for query: {query}")
            return []

        # Step 2: Get view counts with videos.list
        videos_request = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids)
        )
        videos_response = videos_request.execute()

        # Filter videos with >100k views
        filtered_videos = []
        for item in videos_response.get("items", []):
            view_count = int(item["statistics"].get("viewCount", 0))
            if view_count > 100000:  # 100k views
                filtered_videos.append({
                    "url": f"https://youtu.be/{item['id']}",
                    "title": item["snippet"]["title"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                    "views": view_count
                })

        # Sort by views (descending) and take top 3
        filtered_videos.sort(key=lambda x: x["views"], reverse=True)
        logging.info(f"Filtered videos for {query}: {len(filtered_videos)} found")
        return filtered_videos[:3]

    except Exception as e:
        logging.error(f"Error fetching videos: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        niche = request.form.get('niche', '').strip()
        if niche:
            trends = get_trending_topics(niche)
            tweet_video_pairs = []
            for trend in trends:
                tweets = generate_x_posts(trend)
                for tweet in tweets:
                    videos = get_youtube_video_options(f"{niche} {trend}")
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
        logging.error(f"Error scheduling: {e}")
    return redirect(url_for('home'))

if __name__ == "__main__":
    print("Starting web interface at http://127.0.0.1:5000")
    app.run(debug=True)