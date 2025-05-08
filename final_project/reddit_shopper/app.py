from pinecone import Pinecone
import streamlit as st
import requests
import hashlib
import time
from sentence_transformers import SentenceTransformer

# === Config ===
PINECONE_INDEX = "reddit-shopper"
NAMESPACE = "reddit-namespace"

# === Initialize Pinecone and Embedder ===
pc = Pinecone(api_key="pcsk_3aTBe3_QBE6WK7Q97V5Rb7VrAtrwDUFpVGzaNhHxNgJgwSqJduuQAE7bt2SQgmRxaPGG1Y")
index = pc.Index(name="reddit-shopper", host="https://reddit-shopper-thxz7zo.svc.aped-4627-b74a.pinecone.io")
model = SentenceTransformer("all-MiniLM-L6-v2")
embed = lambda text: model.encode(text).tolist()

# === Reddit Scraping Functions ===
def search_reddit(query, limit=20, sort='top', timeframe='month'):
    query = query.replace(' ', '+')
    url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort={sort}&t={timeframe}"
    r = requests.get(url, headers={'User-agent': 'streamlit-reddit-bot'})
    return r.json().get('data', {}).get('children', [])

def get_comments(post_url):
    try:
        r = requests.get(post_url + ".json", headers={'User-agent': 'streamlit-reddit-bot'})
        data = r.json()
        comments = [item['data']['body'] for item in data[1]['data']['children'] if 'body' in item['data']]
        return comments
    except:
        return []

def is_reviewer_comment(text, min_words=50):
    keywords = ['i tried', 'i tested', 'in my experience', 'this product', 'works great', 'did not like', 'pros and cons', 'overall', 'would recommend', 'not worth']
    text_l = text.lower()
    return len(text.split()) >= min_words and any(kw in text_l for kw in keywords)

def upsert_comment(comment_id, text, metadata):
    vec = embed(text)
    index.upsert(vectors=[{
        "id": comment_id,
        "values": vec,
        "metadata": metadata
    }], namespace=NAMESPACE)

# === Streamlit UI ===
st.title("Reddit Semantic Review Indexer")

st.header("Step 1: Scrape and Index Reddit Content")
topic = st.text_input("Enter a Reddit search topic", "hot weather hiking pants")

if st.button("Scrape & Upload"):
    with st.spinner("Scraping posts and filtering comments..."):
        posts = search_reddit(topic)
        count = 0
        for post in posts:
            title = post['data']['title']
            permalink = post['data']['permalink']
            post_url = f"https://www.reddit.com{permalink}"
            comments = get_comments(post_url)
            for comment in comments:
                if is_reviewer_comment(comment):
                    comment_id = hashlib.md5(comment.encode()).hexdigest()
                    metadata = {"post_title": title, "chunk_text": comment, "category": topic}
                    upsert_comment(comment_id, comment, metadata)
                    count += 1
            time.sleep(1)
        st.success(f"Done! Indexed {count} reviewer-style comments.")

st.header("Step 2: Search Indexed Comments")
query = st.text_input("Search for specific insights (e.g., breathability, durability)", "are they breathable")

if st.button("Search Comments"):
    try:
        results = index.query(
            vector=embed(query),
            top_k=10,
            include_metadata=True,
            namespace=NAMESPACE
        )
        st.subheader("Top Matching Comments")
        for match in results['matches']:
            metadata = match['metadata']
            st.markdown(f"**Post Title:** {metadata.get('post_title', 'N/A')}")
            st.markdown(f"**Category:** {metadata.get('category', 'N/A')}")
            st.markdown(f"**Score:** {match['score']:.3f}")
            st.markdown(metadata.get("chunk_text", "No comment found"))
            st.markdown("---")
    except Exception as e:
        st.error(f"Search error: {e}")
