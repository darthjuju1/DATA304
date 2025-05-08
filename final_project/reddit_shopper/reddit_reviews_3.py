import streamlit as st
import pandas as pd
import hashlib
from textblob import TextBlob
import matplotlib.pyplot as plt
from pinecone import Pinecone
import time

# === Config ===
PINECONE_API_KEY = "pcsk_3aTBe3_QBE6WK7Q97V5Rb7VrAtrwDUFpVGzaNhHxNgJgwSqJduuQAE7bt2SQgmRxaPGG1Y"
PINECONE_INDEX = "reddit-shopper"
NAMESPACE = "reddit-namespace"

# === Initialize Pinecone ===
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX, host="https://reddit-shopper-thxz7zo.svc.aped-4627-b74a.pinecone.io")

review_keywords = [
    'i tried', 'i tested', 'in my experience', 'this product', 'works great',
    'did not like', 'pros and cons', 'overall', 'would recommend', 'not worth'
]

# === Analysis Function ===
def analyze_keyword_vs_semantic(df, query, pinecone_index, reviewer_keywords):
    """
    Compare keyword search vs semantic search on comment relevance.
    """
    keyword_matches = df[df['comment'].str.contains(query, case=False, na=False)].copy()
    keyword_matches['method'] = 'keyword'

    semantic_matches = []
    progress = st.progress(0)
    for i, row in df.iterrows():
        comment = row['comment']
        temp_id = hashlib.md5(comment.encode()).hexdigest()
        try:
            pinecone_index.upsert_records("temp-semantic-check", [{
                "_id": temp_id,
                "chunk_text": comment
            }])
            result = pinecone_index.search(
                namespace="temp-semantic-check",
                query={"inputs": {"text": query}, "top_k": 1},
                fields=["chunk_text"]
            )
            score = result['result']['hits'][0]['_score']
            if score >= 0.5:
                semantic_matches.append({
                    "comment": comment,
                    "method": "semantic"
                })
        except:
            continue
        finally:
            pinecone_index.delete(namespace="temp-semantic-check", ids=[temp_id])
        progress.progress((i + 1) / len(df))

    semantic_df = pd.DataFrame(semantic_matches)
    combined = pd.concat([keyword_matches[['comment', 'method']], semantic_df], ignore_index=True)

    combined['is_reviewer'] = combined['comment'].apply(
        lambda x: any(kw in x.lower() for kw in reviewer_keywords)
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

    return summary

# === Streamlit UI ===
st.title("🔬 Semantic vs Keyword Search Effectiveness")

uploaded_file = st.file_uploader("Upload a CSV with columns: 'comment', 'title'", type=["csv"])

query = st.text_input("Enter a query for analysis", "breathable")

if uploaded_file and st.button("Run Analysis"):
    df = pd.read_csv(uploaded_file)
    if 'comment' not in df.columns:
        st.error("CSV must contain a 'comment' column.")
    else:
        analyze_keyword_vs_semantic(df, query, index, review_keywords)