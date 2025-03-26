import tweepy
import random
from googleapiclient.discovery import build
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for
import json

# Load environment variables from .env
load_dotenv()
project_root = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_root, "bot.log")
scheduled_file = os.path.join(project_root, "scheduled_posts.json")
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# X API setup (Free tier - posting only)
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
client = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN,
                       access_token_secret=ACCESS_TOKEN_SECRET)

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache=None)

app = Flask(__name__)


# Load scheduled posts from JSON file
def load_scheduled_posts():
    if os.path.exists(scheduled_file):
        with open(scheduled_file, 'r') as f:
            return json.load(f)
    return []


# Save scheduled posts to JSON file
def save_scheduled_posts(posts):
    with open(scheduled_file, 'w') as f:
        json.dump(posts, f, indent=4)


scheduled_posts = load_scheduled_posts()


def get_youtube_video_options(query, min_views, date_range, duration_filter):
    """Fetch 3 YouTube videos with user-selected filters, with fallback if needed."""
    try:
        # Set date filter
        published_after = None
        if date_range == "last_month":
            published_after = (datetime.now() - timedelta(days=30)).isoformat() + "Z"
        elif date_range == "last_3_months":
            published_after = (datetime.now() - timedelta(days=90)).isoformat() + "Z"
        elif date_range == "last_6_months":
            published_after = (datetime.now() - timedelta(days=180)).isoformat() + "Z"

        # Set duration filter
        video_duration = None
        if duration_filter == "short":
            video_duration = "short"
        elif duration_filter == "medium":
            video_duration = "medium"
        elif duration_filter == "long":
            video_duration = "long"

        search_request = youtube.search().list(
            part="snippet",
            maxResults=20,
            q=query + " tutorial -inurl:(live stream)",
            type="video",
            videoDuration=video_duration,
            publishedAfter=published_after
        )
        search_response = search_request.execute()
        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        logging.info(f"Initial search for '{query}': {len(video_ids)} videos found")

        if not video_ids:
            logging.info(f"No videos found for query: {query}")
            return []

        # Get view counts, details, and duration
        videos_request = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=",".join(video_ids)
        )
        videos_response = videos_request.execute()

        # Define view count thresholds
        view_thresholds = [
            {"key": "100k", "value": 100000},
            {"key": "50k", "value": 50000},
            {"key": "10k", "value": 10000},
            {"key": "any", "value": 0}
        ]

        # Find the starting threshold based on user selection
        min_views_value = next((t["value"] for t in view_thresholds if t["key"] == min_views), 0)
        threshold_index = next((i for i, t in enumerate(view_thresholds) if t["value"] == min_views_value),
                               len(view_thresholds) - 1)

        filtered_videos = []
        # Try each threshold from the selected one down to "any"
        for i in range(threshold_index, len(view_thresholds)):
            current_threshold = view_thresholds[i]["value"]
            current_key = view_thresholds[i]["key"]
            logging.info(f"Trying view count filter ({current_key}) for '{query}'")

            for item in videos_response.get("items", []):
                view_count = int(item["statistics"].get("viewCount", 0))
                if view_count >= current_threshold and not any(
                        v["url"] == f"https://youtu.be/{item['id']}" for v in filtered_videos):
                    duration = item["contentDetails"]["duration"]
                    logging.debug(f"Raw duration for video {item['id']}: {duration}")
                    try:
                        minutes = 0
                        seconds = 0
                        duration = duration.replace("PT", "")
                        if "M" in duration:
                            minutes_part = duration.split("M")[0]
                            minutes = int(minutes_part) if minutes_part else 0
                            seconds_part = duration.split("M")[1].replace("S", "") if "S" in duration else "0"
                            seconds = int(seconds_part) if seconds_part else 0
                        elif "S" in duration:
                            seconds = int(duration.replace("S", ""))
                        duration_str = f"{minutes}:{seconds:02d}"
                    except Exception as e:
                        logging.warning(f"Failed to parse duration '{duration}' for video {item['id']}: {e}")
                        duration_str = "0:00"

                    filtered_videos.append({
                        "url": f"https://youtu.be/{item['id']}",
                        "title": item["snippet"]["title"],
                        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                        "views": view_count,
                        "published_at": item["snippet"]["publishedAt"],
                        "duration": duration_str
                    })

            logging.info(f"After view count filter ({current_key}) for '{query}': {len(filtered_videos)} videos")
            if len(filtered_videos) >= 3:
                break

        # Sort by views (descending) and take top 3
        filtered_videos.sort(key=lambda x: x["views"], reverse=True)
        final_videos = filtered_videos[:3]
        logging.info(f"Final videos for '{query}': {len(final_videos)} returned")
        return final_videos

    except Exception as e:
        logging.error(f"Error fetching videos: {e}")
        return []


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        min_views = request.form.get('min_views', 'any')
        date_range = request.form.get('date_range', 'any')
        duration_filter = request.form.get('duration_filter', 'any')
        if topic:
            videos = get_youtube_video_options(topic, min_views, date_range, duration_filter)
            logging.info(f"Rendering template with videos: {len(videos)}")
            return render_template('index.html', videos=videos, scheduled=scheduled_posts, topic=topic,
                                   min_views=min_views, date_range=date_range, duration_filter=duration_filter)
    logging.info("Rendering initial template (GET request)")
    return render_template('index.html', videos=None, scheduled=scheduled_posts, topic="",
                           min_views="any", date_range="any", duration_filter="any")


@app.route('/schedule', methods=['POST'])
def schedule():
    tweet = request.form.get('tweet', '').strip()
    video_url = request.form.get('video', '').strip()
    hashtags = request.form.get('hashtags', '').strip()
    post_datetime = request.form.get('post_datetime', '')

    if not tweet or not video_url or not post_datetime:
        logging.warning("Missing required fields in schedule request")
        return redirect(url_for('home'))

    try:
        post_time = datetime.strptime(post_datetime, '%Y-%m-%dT%H:%M')
    except ValueError:
        logging.error(f"Invalid datetime format: {post_datetime}")
        return redirect(url_for('home'))

    message = f"{tweet} Learn more: {video_url}"
    if hashtags:
        message += f" {hashtags}"

    if len(message) > 280:
        message = message[:277] + "..."

    scheduled_posts.append({
        "text": message,
        "time": post_time.strftime("%Y-%m-%d %H:%M"),
        "timestamp": int(post_time.timestamp())
    })
    save_scheduled_posts(scheduled_posts)

    try:
        client.create_tweet(text=message, execute_at=int(post_time.timestamp()))
        logging.info(f"Scheduled: {message} at {post_time}")
    except Exception as e:
        logging.error(f"Error scheduling: {e}")
    return redirect(url_for('home'))


@app.route('/post_now', methods=['POST'])
def post_now():
    tweet = request.form.get('tweet', '').strip()
    video_url = request.form.get('video', '').strip()
    hashtags = request.form.get('hashtags', '').strip()

    if not tweet or not video_url:
        logging.warning("Missing required fields in post_now request")
        return redirect(url_for('home'))

    message = f"{tweet} Learn more: {video_url}"
    if hashtags:
        message += f" {hashtags}"

    if len(message) > 280:
        message = message[:277] + "..."

    try:
        client.create_tweet(text=message)
        logging.info(f"Posted immediately: {message}")
    except Exception as e:
        logging.error(f"Error posting immediately: {e}")
    return redirect(url_for('home'))


@app.route('/remove/<int:index>', methods=['POST'])
def remove(index):
    if 0 <= index < len(scheduled_posts):
        removed_post = scheduled_posts.pop(index)
        save_scheduled_posts(scheduled_posts)
        logging.info(f"Removed scheduled post: {removed_post['text']}")
    return redirect(url_for('home'))


if __name__ == "__main__":
    print("Starting web interface at http://127.0.0.1:5000")
    app.run(debug=True)