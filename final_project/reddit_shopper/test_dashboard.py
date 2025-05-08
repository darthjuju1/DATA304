import streamlit as st
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from textblob import TextBlob
import spacy

# Load spaCy's NLP model
nlp = spacy.load("en_core_web_sm")

# Reddit API credentials
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
USERNAME = "your_username"
PASSWORD = "your_password"
USER_AGENT = "your_script_name"
'''
# Function to get an access token
def get_access_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    headers = {"User-Agent": USER_AGENT}

    response = requests.post("https://www.reddit.com/api/v1/access_token",
                             auth=auth, data=data, headers=headers)
    
    token = response.json().get("access_token")
    return token
'''
# Function to analyze sentiment
def analyze_sentiment(text):
    analysis = TextBlob(text)
    sentiment_score = analysis.sentiment.polarity  # Ranges from -1 to 1
    if sentiment_score > 0:
        sentiment = "Positive"
    elif sentiment_score < 0:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    return sentiment, sentiment_score

# Function to extract keywords
def extract_keywords(text):
    doc = nlp(text)
    keywords = [token.text for token in doc if token.is_alpha and not token.is_stop]
    return keywords

# Function to scrape Reddit posts
def scrape_reddit_posts(subreddit, limit=10):
    token = "2449066273928-W9nPRumJYfj87DNZ5SGN5w8h51Z7ig"#get_access_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
    
    url = f"https://oauth.reddit.com/r/{subreddit}/hot?limit={limit}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        posts = response.json()["data"]["children"]
        results = []
        for post in posts:
            title = post["data"]["title"]
            url = post["data"]["url"]
            sentiment, score = analyze_sentiment(title)
            keywords = extract_keywords(title)

            results.append({
                "title": title,
                "url": url,
                "sentiment": sentiment,
                "sentiment_score": score,
                "keywords": ", ".join(keywords)
            })
        
        return results
    else:
        return []

# Streamlit App Layout
st.title("Reddit Sentiment Analysis Dashboard")

# Sidebar Input
subreddit = st.sidebar.text_input("Enter Subreddit", "technology")
post_limit = st.sidebar.slider("Number of Posts", 5, 50, 10)

# Scrape Data
if st.sidebar.button("Analyze"):
    st.sidebar.write("Fetching data...")
    posts = scrape_reddit_posts(subreddit, post_limit)

    if posts:
        df = pd.DataFrame(posts)
        
        # Display Data Table
        st.subheader(f"Sentiment Analysis for r/{subreddit}")
        st.write(df)

        # Sentiment Distribution
        st.subheader("Sentiment Breakdown")
        sentiment_counts = df["sentiment"].value_counts()
        st.bar_chart(sentiment_counts)

        # Word Cloud for Keywords
        st.subheader("Keyword Word Cloud")
        all_keywords = " ".join(df["keywords"])
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_keywords)
        
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

    else:
        st.write("Failed to fetch data. Try again later.")
