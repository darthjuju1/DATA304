#WORKING, but not what i'm looking for


import streamlit as st
import requests
import time

import streamlit as st
import requests
import time

# === Functions ===

def search_reddit(query, limit=100, sort='relevance', timeframe='all'):
    query = query.replace(' ', '+')
    base_url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort={sort}&t={timeframe}"
    try:
        response = requests.get(base_url, headers={'User-agent': 'yourbot'})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return None
    return response.json()

def get_post_comments(post_url):
    headers = {'User-agent': 'yourbot'}
    try:
        response = requests.get(post_url + ".json", headers=headers)
        response.raise_for_status()
        data = response.json()
        comments = [c['data']['body'] for c in data[1]['data']['children'] if 'body' in c['data']]
        return comments
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching comments: {e}")
        return []

def is_reviewer_style_comment(text, min_word_count=50):
    review_keywords = ["i tested", "i tried", "in my experience", "pros and cons", "durability",
        "breathable", "fit well", "sizing", "material", "not worth", "worth it",
        "comfort", "recommend", "lightweight", "too tight", "too loose", "overall"]
    text_lower = text.lower()
    return len(text.split()) >= min_word_count and any(kw in text_lower for kw in review_keywords)

def get_all_comments(posts_json, post_limit=10):
    posts_with_comments = []
    for i, post in enumerate(posts_json['data']['children']):
        if i >= post_limit:
            break
        post_url = "https://www.reddit.com" + post['data']['permalink']
        title = post['data']['title']
        st.write(f"📥 Fetching comments for: **{title}**")
        comments = get_post_comments(post_url)
        filtered = [c for c in comments if is_reviewer_style_comment(c)]
        if filtered:
            posts_with_comments.append({
                "title": title,
                "url": post_url,
                "comments": filtered
            })
        time.sleep(1)
    return posts_with_comments

# === Streamlit UI ===

st.title("🔍 Reddit Review Comment Extractor")

query = st.text_input("Enter a product/topic to search on Reddit", "hot weather hiking pants")

if st.button("Search Reddit"):
    with st.spinner("Searching Reddit and analyzing comments..."):
        search_results = search_reddit(query, limit=20, sort='top', timeframe='month')
        if search_results:
            results = get_all_comments(search_results, post_limit=5)
            st.success(f"Found {len(results)} posts with quality review comments.")
            for post in results:
                st.markdown(f"### 📝 {post['title']}")
                st.markdown(f"[View on Reddit]({post['url']})")
                for comment in post['comments']:
                    st.markdown(f"> {comment}")
                st.markdown("---")

# === Functions ===

def search_reddit(query, limit=100, sort='relevance', timeframe='all'):
    query = query.replace(' ', '+')
    base_url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort={sort}&t={timeframe}"
    try:
        response = requests.get(base_url, headers={'User-agent': 'yourbot'})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return None
    return response.json()


def get_post_comments(post_url):
    headers = {'User-agent': 'yourbot'}
    try:
        response = requests.get(post_url + ".json", headers=headers)
        response.raise_for_status()
        data = response.json()
        comments = [c['data']['body'] for c in data[1]['data']['children'] if 'body' in c['data']]
        return comments
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching comments: {e}")
        return []

def is_reviewer_style_comment(text, min_word_count=50):
    review_keywords = ['i tried', 'i tested', 'in my experience', 'this product', 
                       'works great', 'did not like', 'pros and cons', 'overall', 'would recommend', 'not worth']
    text_lower = text.lower()
    return len(text.split()) >= min_word_count and any(kw in text_lower for kw in review_keywords)

def get_all_comments(posts_json, post_limit=10):
    posts_with_comments = []
    for i, post in enumerate(posts_json['data']['children']):
        if i >= post_limit:
            break
        post_url = "https://www.reddit.com" + post['data']['permalink']
        title = post['data']['title']
        st.write(f"📥 Fetching comments for: **{title}**")
        comments = get_post_comments(post_url)
        filtered = [c for c in comments if is_reviewer_style_comment(c)]
        if filtered:
            posts_with_comments.append({
                "title": title,
                "url": post_url,
                "comments": filtered
            })
        time.sleep(1)
    return posts_with_comments

# === Streamlit UI ===

st.title("🔍 Reddit Review Comment Extractor")

query = st.text_input("Enter a product/topic to search on Reddit", "hot weather hiking pants")

if st.button("Search Reddit"):
    with st.spinner("Searching Reddit and analyzing comments..."):
        search_results = search_reddit(query, limit=20, sort='top', timeframe='month')
        if search_results:
            results = get_all_comments(search_results, post_limit=5)
            st.success(f"Found {len(results)} posts with quality review comments.")
            for post in results:
                st.markdown(f"### 📝 {post['title']}")
                st.markdown(f"[View on Reddit]({post['url']})")
                for comment in post['comments']:
                    st.markdown(f"> {comment}")
                st.markdown("---")
