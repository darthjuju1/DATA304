import streamlit as st
import requests
import hashlib
import time
import pandas as pd
from pinecone import Pinecone

# === Config ===
PINECONE_API_KEY = "pcsk_3aTBe3_QBE6WK7Q97V5Rb7VrAtrwDUFpVGzaNhHxNgJgwSqJduuQAE7bt2SQgmRxaPGG1Y"
PINECONE_INDEX = "reddit-shopper"
NAMESPACE = "reddit-namespace"

# === Initialize Pinecone ===
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX, host="https://reddit-shopper-thxz7zo.svc.aped-4627-b74a.pinecone.io")

# === Reddit Functions ===
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
    keywords = ['i tried', 'i tested', 'in my experience', 'this product', 'works great', 'did not like', 'pros and cons', 'overall', 'would recommend', 'not worth']
    text_l = text.lower()
    return len(text.split()) >= min_words and any(kw in text_l for kw in keywords)

def is_semantically_relevant(comment_text, query, threshold=0.5):
    temp_ns = "temp-comment-check"
    temp_id = hashlib.md5(comment_text.encode()).hexdigest()
    try:
        index.upsert_records(temp_ns, [{
            "_id": temp_id,
            "chunk_text": comment_text
        }])
        result = index.search(
            namespace=temp_ns,
            query={"inputs": {"text": query}, "top_k": 1},
            fields=["chunk_text"]
        )
        score = result['result']['hits'][0]['_score']
        return score >= threshold
    except:
        return False
    finally:
        index.delete(namespace=temp_ns, ids=[temp_id])

def filter_relevant_posts(posts, query, top_n=10):
    temp_namespace = "temp-title-rank"
    top_titles = []
    for i, post in enumerate(posts):
        title = post['data']['title']
        temp_id = f"title-{i}-{hashlib.md5(title.encode()).hexdigest()}"
        index.upsert_records(temp_namespace, [{
            "_id": temp_id,
            "chunk_text": title
        }])
        try:
            result = index.search(
                namespace=temp_namespace,
                query={"inputs": {"text": query}, "top_k": 1},
                fields=["chunk_text"]
            )
            if result['result']['hits'] and result['result']['hits'][0]['_score'] > 0.3:
                top_titles.append(title)
        except:
            continue
        finally:
            index.delete(namespace=temp_namespace, ids=[temp_id])
    return [post for post in posts if post['data']['title'] in top_titles]

# === Streamlit App ===
st.title("Reddit Semantic Review Indexer")

st.header("Step 1: Scrape and Index Reddit Content")
topic = st.text_input("Enter a Reddit search topic", "hot weather hiking pants")
threshold = st.slider("Semantic Relevance Threshold (for comments)", 0.0, 1.0, 0.5, 0.05)

if st.button("Scrape & Upload"):
    with st.spinner("Searching and processing posts..."):
        all_posts = search_reddit(topic)
        top_posts = filter_relevant_posts(all_posts, topic)
        
        records = []
        for post in top_posts:
            title = post['data']['title']
            permalink = post['data']['permalink']
            post_url = f"https://www.reddit.com{permalink}"
            st.write(f"📥 Fetching comments for: **{title}**")
            comments = get_comments(post_url)
            for comment in comments:
                if is_reviewer_comment(comment) and is_semantically_relevant(comment, topic, threshold):
                    records.append({
                        "Post Title": title,
                        "Comment": comment
                    })
            time.sleep(1)

        # Convert to DataFrame and prepare for upsert
        if records:
            df = pd.DataFrame(records)
            df['_id'] = 'rec' + df.index.astype(str)
            records_ready = (
                df[['_id', 'Post Title', 'Comment']]
                .rename(columns={'Post Title': 'title', 'Comment': 'chunk_text'})
                .to_dict(orient='records')
            )
            for rec in records_ready:
                try:
                    index.upsert_records(NAMESPACE, [rec])
                except Exception as e:
                    st.error(f"Upsert error: {e}")
            st.success(f"✅ Indexed {len(records_ready)} comments.")
        else:
            st.warning("No relevant comments found.")

# === Search UI ===
st.header("Step 2: Search Indexed Comments")
query = st.text_input("Search for specific insights (e.g., breathability, durability)", "are they breathable")

if st.button("Search Comments"):
    try:
        results = index.search(
            namespace=NAMESPACE,
            query={"inputs": {"text": query}, "top_k": 10},
            fields=["chunk_text", "title"]
        )
        st.subheader("Top Matching Comments")
        for match in results['result']['hits']:
            metadata = match['fields']
            st.markdown(f"**Post Title:** {metadata.get('title', 'N/A')}")
            st.markdown(f"**Score:** {match['_score']:.3f}")
            st.markdown(metadata.get("chunk_text", "No comment found"))
            st.markdown("---")
    except Exception as e:
        st.error(f"Search error: {e}")
