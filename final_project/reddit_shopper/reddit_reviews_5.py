import streamlit as st
import requests
import hashlib
import time
import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt
from pinecone import Pinecone

# === Config ===
PINECONE_API_KEY = "pcsk_3aTBe3_QBE6WK7Q97V5Rb7VrAtrwDUFpVGzaNhHxNgJgwSqJduuQAE7bt2SQgmRxaPGG1Y"
PINECONE_INDEX = "reddit-shopper"
NAMESPACE = "reddit-namespace"

# === Pinecone Init ===
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX, host="https://reddit-shopper-thxz7zo.svc.aped-4627-b74a.pinecone.io")

review_keywords = [
    'i tried', 'i tested', 'in my experience', 'this product', 'works great',
    'did not like', 'pros and cons', 'overall', 'would recommend', 'not worth'
]

# === Reddit Scraping ===
def search_reddit(query, limit=100, sort='relevance', timeframe='all'):
    query = query.replace(' ', '+')
    url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort={sort}&t={timeframe}"
    r = requests.get(url, headers={'User-agent': 'streamlit-reddit-bot'})
    return r.json().get('data', {}).get('children', [])

def get_comments(post_url):
    try:
        r = requests.get(post_url + ".json", headers={'User-agent': 'streamlit-reddit-bot'})
        data = r.json()
        return [item['data']['body'] for item in data[1]['data']['children'] if 'body' in item['data']]
    except:
        return []

def is_reviewer_comment(text, min_words=50):
    text_l = text.lower()
    return len(text.split()) >= min_words and any(kw in text_l for kw in review_keywords)

def is_semantically_relevant(comment_text, query, threshold=0.5):
    temp_ns = "temp-comment-check"
    temp_id = hashlib.md5(comment_text.encode()).hexdigest()
    try:
        index.upsert_records(temp_ns, [{"_id": temp_id, "chunk_text": comment_text}])
        result = index.search(namespace=temp_ns, query={"inputs": {"text": query}, "top_k": 1}, fields=["chunk_text"])
        score = result['result']['hits'][0]['_score']
        return score >= threshold
    except:
        return False
    finally:
        index.delete(namespace=temp_ns, ids=[temp_id])

def filter_relevant_posts(posts, query):
    temp_ns = "temp-title-rank"
    top_titles = []
    for i, post in enumerate(posts):
        title = post['data']['title']
        temp_id = f"title-{i}-{hashlib.md5(title.encode()).hexdigest()}"
        index.upsert_records(temp_ns, [{"_id": temp_id, "chunk_text": title}])
        try:
            result = index.search(namespace=temp_ns, query={"inputs": {"text": query}, "top_k": 1}, fields=["chunk_text"])
            if result['result']['hits'] and result['result']['hits'][0]['_score'] > 0.3:
                top_titles.append(title)
        except:
            continue
        finally:
            index.delete(namespace=temp_ns, ids=[temp_id])
    return [post for post in posts if post['data']['title'] in top_titles]

# === Analysis Function ===
def analyze_keyword_vs_semantic(df, query):
    keyword_matches = df[df['comment'].str.contains(query, case=False, na=False)].copy()
    keyword_matches['method'] = 'keyword'

    semantic_matches = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        comment = row['comment']
        temp_id = hashlib.md5(comment.encode()).hexdigest()
        try:
            index.upsert_records("temp-semantic-check", [{"_id": temp_id, "chunk_text": comment}])
            result = index.search(namespace="temp-semantic-check", query={"inputs": {"text": query}, "top_k": 1}, fields=["chunk_text"])
            score = result['result']['hits'][0]['_score']
            if score >= 0.5:
                semantic_matches.append({"comment": comment, "method": "semantic"})
        except:
            continue
        finally:
            index.delete(namespace="temp-semantic-check", ids=[temp_id])
        progress.progress((i + 1) / len(df))

    semantic_df = pd.DataFrame(semantic_matches)
    combined = pd.concat([keyword_matches[['comment', 'method']], semantic_df], ignore_index=True)

    combined['is_reviewer'] = combined['comment'].apply(
        lambda x: any(kw in x.lower() for kw in review_keywords)
    )
    combined['sentiment'] = combined['comment'].apply(lambda x: TextBlob(x).sentiment.polarity)
    combined['word_count'] = combined['comment'].apply(lambda x: len(x.split()))

    summary = combined.groupby('method').agg({
        'is_reviewer': 'sum',
        'sentiment': 'mean',
        'word_count': 'mean'
    }).rename(columns={
        'is_reviewer': 'Reviewer-style Count',
        'sentiment': 'Avg. Sentiment',
        'word_count': 'Avg. Length'
    }).reset_index()

    st.subheader("📊 Keyword vs Semantic Comparison")
    st.dataframe(summary)

    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    axs[0].bar(summary['method'], summary['Reviewer-style Count'], color=['orange', 'green'])
    axs[0].set_title("Reviewer-style Count")
    axs[1].bar(summary['method'], summary['Avg. Sentiment'], color=['orange', 'green'])
    axs[1].set_title("Avg Sentiment")
    axs[2].bar(summary['method'], summary['Avg. Length'], color=['orange', 'green'])
    axs[2].set_title("Avg Word Count")
    for ax in axs:
        ax.set_xlabel("Method")
    plt.tight_layout()
    st.pyplot(fig)

# === UI ===
st.title("Reddit Semantic Review Indexer")

st.header("Step 1: Scrape and Index Reddit Content")
topic = st.text_input("Enter a Reddit search topic", "hot weather hiking pants")
threshold = st.slider("Semantic Relevance Threshold (for comments)", 0.0, 1.0, 0.5, 0.05)

if st.button("Scrape & Upload"):
    all_posts = search_reddit(topic)
    top_posts = filter_relevant_posts(all_posts, topic)
    records = []
    for post in top_posts:
        title = post['data']['title']
        post_url = f"https://www.reddit.com{post['data']['permalink']}"
        st.write(f"Fetching comments for: **{title}**")
        comments = get_comments(post_url)
        for comment in comments:
            if is_reviewer_comment(comment) and is_semantically_relevant(comment, topic, threshold):
                records.append({"title": title, "comment": comment})
        time.sleep(1)

    if records:
        comments_df = pd.DataFrame(records)
        comments_df['_id'] = 'rec' + comments_df.index.astype(str)
        for rec in comments_df.to_dict(orient='records'):
            index.upsert_records(NAMESPACE, [{"_id": rec['_id'], "title": rec['title'], "chunk_text": rec['comment']}])
        st.session_state['comments_df'] = comments_df
        st.success(f"Indexed {len(comments_df)} comments.")
        st.download_button("Download Indexed Comments", data=comments_df.to_csv(index=False).encode('utf-8'), file_name="indexed_comments.csv", mime="text/csv")
    else:
        st.warning("No relevant comments found.")

# === Step 2: Analysis ===
st.header("Step 2: Analyze Keyword vs Semantic Match Effectiveness")

if 'comments_df' in st.session_state and not st.session_state['comments_df'].empty:
    comments_df = st.session_state['comments_df']
    st.info("Using comments from your last scrape.")
    query = st.text_input("Enter a sub-query to test effectiveness", "breathable")
    if st.button("Run Analysis"):
        analyze_keyword_vs_semantic(comments_df, query)
else:
    st.info("Scrape comments first to enable this analysis.")
