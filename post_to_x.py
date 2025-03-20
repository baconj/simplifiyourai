import tweepy
import schedule
import time
import random
from googleapiclient.discovery import build
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(project_root, "bot.log")

# Configure logging
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Your X API credentials
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def get_grok_tip():
    tips = [
        ("AI tip: Use Grok to write X posts with affiliate links. Post 3x/day to grow @simplifiyourai. #AIhustle",
         "affiliate marketing tutorial"),
        (
        "Automate your income: Let AI reply to X comments with value. Link to your Medium for affiliate $$ @simplifiyourai #AIhustle",
        "automate social media replies"),
        (
        "AI hack: Scrape X trends with a bot, then post affiliate products. Start free with Python @simplifiyourai #AIhustle",
        "scrape social media trends"),
        (
        "Passive income idea: Use AI to write eBooks, sell on Gumroad. I can help with the content @simplifiyourai #AIhustle",
        "write ebooks with ai"),
        ("Grow your X following: Post AI-generated tips daily. Follow @simplifiyourai for more #AIhustle",
         "grow social media following"),
        (
        "AI automation: Use Zapier + AI to send emails with affiliate links. Low effort, high reward @simplifiyourai #AIhustle",
        "zapier affiliate marketing"),
        (
        "Monetize X: Share AI tips, drive traffic to a $7 cheat sheet. I can write it for you @simplifiyourai #AIhustle",
        "monetize social media"),
        ("AI side hustle: Create AI-generated art with DALL-E, sell as NFTs. Start small @simplifiyourai #AIhustle",
         "ai generated art nft"),
        (
        "Automate lead gen: Use AI to find X users in your niche, pitch affiliate offers via DM @simplifiyourai #AIhustle",
        "automate lead generation"),
        ("AI content hack: Repurpose X threads into blog posts with AI. Monetize with ads @simplifiyourai #AIhustle",
         "repurpose social media content"),
        ("Use AI to write LinkedIn posts, drive traffic to your X. Cross-platform growth @simplifiyourai #AIhustle",
         "ai linkedin posts"),
        (
        "AI email hack: Automate personalized emails with AI, include affiliate links. Scale with Mailchimp @simplifiyourai #AIhustle",
        "ai email marketing"),
        ("Create an AI chatbot for your niche, offer it as a service. Charge monthly @simplifiyourai #AIhustle",
         "create ai chatbot"),
        ("AI SEO: Use AI to write keyword-rich blog posts, rank on Google, monetize with ads @simplifiyourai #AIhustle",
         "ai seo blog posts"),
        (
        "Automate YouTube: Use AI to script videos, edit with Descript, monetize with affiliate links @simplifiyourai #AIhustle",
        "ai youtube automation"),
        (
        "AI growth hack: Use AI to analyze X data, find viral topics, and post about them. Grow fast @simplifiyourai #AIhustle",
        "analyze social media data"),
        (
        "Monetize your skills: Use AI to create online courses, sell on Udemy. I can help with scripts @simplifiyourai #AIhustle",
        "create online courses ai"),
        ("AI affiliate tip: Promote AI tools on X, earn commissions. Start with free trials @simplifiyourai #AIhustle",
         "promote ai tools affiliate"),
        ("Automate Pinterest: Use AI to design pins, link to your blog with affiliate offers @simplifiyourai #AIhustle",
         "ai pinterest automation"),
        ("AI productivity: Let AI summarize X threads into actionable tips. Share and grow @simplifiyourai #AIhustle",
         "ai summarize social media"),
        (
        "AI money hack: Use AI to transcribe podcasts, turn them into blog posts, monetize with ads @simplifiyourai #AIhustle",
        "transcribe podcasts with ai"),
        (
        "Automate TikTok: Use AI to script short videos, post daily, link to affiliate offers @simplifiyourai #AIhustle",
        "ai tiktok automation"),
        ("AI freelance tip: Use AI to write proposals, win gigs on Upwork. Scale your income @simplifiyourai #AIhustle",
         "ai freelance proposals"),
        ("Monetize Instagram: Use AI to design Reels, promote affiliate products in bio @simplifiyourai #AIhustle",
         "ai instagram reels"),
        (
        "AI research hack: Use AI to summarize industry reports, share insights on X, grow your brand @simplifiyourai #AIhustle",
        "ai summarize reports"),
        ("Passive income: Use AI to create print-on-demand designs, sell on Etsy. Low effort @simplifiyourai #AIhustle",
         "ai print on demand"),
        (
        "AI networking: Use AI to draft personalized outreach messages, connect with influencers on X @simplifiyourai #AIhustle",
        "ai networking messages"),
        (
        "Monetize a newsletter: Use AI to write weekly emails, include affiliate links, grow with Substack @simplifiyourai #AIhustle",
        "ai newsletter substack"),
        (
        "AI ad copy: Use AI to write high-converting ad copy, run FB ads, promote affiliate offers @simplifiyourai #AIhustle",
        "ai ad copy facebook"),
        (
        "Automate reviews: Use AI to write product reviews, post on a blog, earn affiliate commissions @simplifiyourai #AIhustle",
        "ai product reviews affiliate")
    ]
    return random.choice(tips)


def get_youtube_video(query):
    try:
        request = youtube.search().list(
            part="snippet",
            maxResults=1,
            q=query,
            type="video"
        )
        response = request.execute()
        if response["items"]:
            video_id = response["items"][0]["id"]["videoId"]
            return f"https://youtu.be/{video_id}"
        return None
    except Exception as e:
        logging.error(f"Error fetching YouTube video: {e}")
        return None


def post_to_x():
    tip, search_query = get_grok_tip()
    video_url = get_youtube_video(search_query)

    if video_url:
        message = f"{tip} Learn more: {video_url}"
    else:
        message = tip

    if len(message) > 280:
        message = message[:277] + "..."

    try:
        client.create_tweet(text=message)
        logging.info(f"Posted: {message}")
    except Exception as e:
        logging.error(f"Error posting: {e}")


schedule.every(8).hours.do(post_to_x)

if __name__ == "__main__":
    post_to_x()
    while True:
        schedule.run_pending()
        time.sleep(60)