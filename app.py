import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
import re
import requests
from io import StringIO

# Common English stop words
STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were',
    'will', 'with', 'the', 'this', 'but', 'they', 'have', 'had', 'what', 'when',
    'where', 'who', 'which', 'why', 'can', 'could', 'should', 'would', 'may',
    'might', 'must', 'shall', 'into', 'if', 'then', 'else', 'than', 'too', 'very',
    'just', 'about', 'also', 'much', 'any', 'only', 'some', 'such', 'more', 'most',
    'other', 'own', 'same', 'few', 'both', 'those', 'after', 'before', 'above',
    'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'once', 'all',
    'always', 'never', 'now', 'ever', 'while', 'during', 'within', 'without',
    'through', 'between', 'against', 'until', 'unless', 'within', 'along', 'across',
    'behind', 'beyond', 'near', 'among', 'upon', 'since', 'despite', 'beside',
    'besides', 'however', 'therefore', 'although', 'yet', 'still', 'even', 'otherwise',
    'says', 'said', 'according', 'new', 'one', 'two', 'three', 'first', 'second',
    'third', 'last', 'next', 'best', 'worst', 'least', 'many', 'another', 'get',
    'got', 'getting', 'every', 'each', 'either', 'neither', 'rather', 'quite',
    'enough', 'less', 'way', 'ways', 'far', 'further', 'later', 'earlier', 'early',
    'late', 'soon', 'already', 'not', 'nor', 'like', 'hard', 'high', 'low'
}

# Add crypto-specific words to stop words
CRYPTO_STOP_WORDS = STOP_WORDS | {
    'bitcoin', 'btc', 'crypto', 'cryptocurrency', 'cryptocurrencies', 'blockchain',
    'token', 'tokens', 'coin', 'coins', 'digital', 'currency', 'currencies',
    'mining', 'miner', 'miners', 'wallet', 'wallets', 'exchange', 'exchanges',
    'trading', 'trader', 'traders', 'market', 'markets', 'price', 'prices'
}

# GitHub raw content URL for the CSV file
GITHUB_CSV_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/sentiment_scores.csv"

# Add cache with TTL of 5 minutes
@st.cache_data(ttl=300)
def load_and_process_data():
    """Load and process sentiment data from GitHub"""
    try:
        # Fetch data from GitHub
        response = requests.get(GITHUB_CSV_URL)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Read CSV from the response content
        df = pd.read_csv(StringIO(response.text))
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date
        df = df.sort_values('date')
        
        # Calculate daily sentiment
        daily_sentiment = df.groupby('date').agg({
            'score': 'mean',
        }).reset_index()
        
        # Calculate moving averages
        daily_sentiment['MA3'] = daily_sentiment['score'].rolling(window=3).mean()
        daily_sentiment['MA7'] = daily_sentiment['score'].rolling(window=7).mean()
        
        return df, daily_sentiment
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def get_sentiment_status(sentiment_df):
    """Determine overall sentiment status based on current sentiment and trends"""
    latest = sentiment_df.iloc[-1]
    
    # Get current sentiment score
    current_sentiment = latest['score']
    short_trend = latest['MA3'] - latest['MA7']
    medium_trend = latest['MA7'] - latest['MA7'].shift(1)
    
    # Scoring system (0-100)
    base_score = (current_sentiment + 1) * 50  # Convert -1 to 1 range to 0-100
    trend_score = (short_trend + medium_trend) * 10  # Add/subtract points for trends
    
    final_score = min(max(base_score + trend_score, 0), 100)  # Ensure score is between 0 and 100
    
    # Determine status
    if final_score >= 60:
        return "BULLISH", final_score, "Positive sentiment with stable/upward trend"
    elif final_score >= 40:
        return "NEUTRAL", final_score, "Mixed or neutral sentiment signals"
    else:
        return "BEARISH", final_score, "Negative sentiment or declining trends"

def extract_topic_words(df):
    """Extract most frequent words from recent titles"""
    if df is None or len(df) == 0:
        return []
    
    # Get articles from last 7 days
    last_date = df['date'].max()
    seven_days_ago = last_date - pd.Timedelta(days=7)
    recent_articles = df[df['date'] >= seven_days_ago]
    
    # Extract words from titles
    keywords = []
    for title in recent_articles['title']:
        if isinstance(title, str):
            words = title.lower().split()
            keywords.extend([word for word in words if len(word) > 3 and word not in CRYPTO_STOP_WORDS])
    
    # Count and rank keywords
    keyword_counts = Counter(keywords)
    return keyword_counts.most_common(5)

def create_alerts(sentiment_df):
    """Generate alerts based on significant changes in sentiment"""
    alerts = []
    
    # Sentiment change alerts
    recent_sentiment = sentiment_df.iloc[-3:]
    if len(recent_sentiment) > 1 and abs(recent_sentiment['score'].diff().iloc[-1]) > 0.2:
        alerts.append(f"Significant sentiment shift detected: {recent_sentiment['score'].iloc[-1]:.2f}")
    
    # Moving average alerts
    if sentiment_df['MA3'].iloc[-1] > sentiment_df['MA7'].iloc[-1] and \
       sentiment_df['MA3'].iloc[-2] <= sentiment_df['MA7'].iloc[-2]:
        alerts.append("Short-term sentiment crossing above medium-term")
    elif sentiment_df['MA3'].iloc[-1] < sentiment_df['MA7'].iloc[-1] and \
         sentiment_df['MA3'].iloc[-2] >= sentiment_df['MA7'].iloc[-2]:
        alerts.append("Short-term sentiment crossing below medium-term")
    
    return alerts

def create_dashboard():
    st.set_page_config(page_title="Crypto News Sentiment Dashboard", layout="wide")
    
    st.title("Crypto News Sentiment Analysis Dashboard")
    st.markdown("---")
    
    # Load data
    df, daily_sentiment = load_and_process_data()
    
    if daily_sentiment is None:
        st.error("Failed to load data. Please check the error message above.")
        return
    
    # Get sentiment status
    status, score, description = get_sentiment_status(daily_sentiment)
    
    # Create layout
    col1, col2, col3 = st.columns([2, 3, 3])
    
    # Sentiment Traffic Light
    with col1:
        st.subheader("Market Sentiment")
        color = {"BULLISH": "🟢", "NEUTRAL": "🟡", "BEARISH": "🔴"}[status]
        st.markdown(f"# {color} {status}")
        st.metric("Sentiment Score", f"{score:.1f}/100")
        st.markdown("""
        <div style='color: gray; font-size: 0.9em; margin-top: -10px;'>
        Combined score (0-100) based on current sentiment and trends.<br>
        🔴 < 40 | 🟡 40-60 | 🟢 > 60
        </div>
        """, unsafe_allow_html=True)
        st.write(description)
    
    # Key Metrics
    with col2:
        st.subheader("Key Metrics")
        current_sentiment = daily_sentiment['score'].iloc[-1]
        sentiment_color = "green" if current_sentiment > 0 else "red"
        st.markdown(f"""
        <div style='font-size: 1.1em'>
        Current Sentiment: <span style='color:{sentiment_color}'>{current_sentiment:.3f}</span>
        </div>
        <div style='color: gray; font-size: 0.9em;'>
        Raw sentiment score (-1 to 1) for the latest day
        </div>
        """, unsafe_allow_html=True)
        
        # Trend Indicators
        st.markdown("### Trend Indicators")
        col2_1, col2_2 = st.columns([3, 1])  
        with col2_1:
            st.markdown("""
            <div style='margin-bottom: 12px;'>3-Day Average:</div>
            <div style='margin-bottom: 12px;'>7-Day Average:</div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div style='color: gray; font-size: 0.9em;'>
            Short-term trend (3 days)<br>
            Medium-term trend (7 days)
            </div>
            """, unsafe_allow_html=True)
        with col2_2:
            trend_short = daily_sentiment['MA3'].iloc[-1]
            trend_medium = daily_sentiment['MA7'].iloc[-1]
            st.markdown("""
            <style>
            .trend-arrow {
                font-size: 28px;
                font-weight: bold;
                text-align: center;
                margin-top: -8px;
                margin-bottom: 12px;
            }
            .trend-up { color: #28a745; }
            .trend-down { color: #dc3545; }
            </style>
            """, unsafe_allow_html=True)
            
            for trend in [trend_short, trend_medium]:
                if trend > 0:
                    st.markdown("""
                    <div class='trend-arrow trend-up'>△</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class='trend-arrow trend-down'>▽</div>
                    """, unsafe_allow_html=True)
    
    # Latest Alerts and News
    with col3:
        st.subheader("Latest Updates")
        
        # Alerts
        alerts = create_alerts(daily_sentiment)
        if alerts:
            st.markdown("#### 🚨 Alerts")
            for alert in alerts:
                st.warning(f"⚠️ {alert}")
        
        # Recent News
        st.subheader("Recent News")
        recent_articles = df.sort_values('date', ascending=False).head(5)
        for _, article in recent_articles.iterrows():
            sentiment_color = "green" if article['score'] > 0 else "red"
            sentiment_icon = "↗" if article['score'] > 0 else "↘"
            st.markdown(f"""
            <div style='border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px;'>
                <div style='color: {sentiment_color}; float: right; font-size: 1.2em;'>{sentiment_icon}</div>
                <div style='font-size: 0.9em;'>{article['title']}</div>
                <div style='font-size: 0.8em; color: gray; margin-top: 5px;'>
                    {article['date'].strftime('%Y-%m-%d')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sentiment Chart
    st.subheader("Sentiment Trends")
    st.markdown("""
    <div style='color: gray; font-size: 0.9em; margin-bottom: 10px;'>
    Blue line: Daily sentiment | Green dotted: 3-day average | Red dotted: 7-day average | Red vertical: Election date
    </div>
    """, unsafe_allow_html=True)
    
    fig = go.Figure()
    
    # Add sentiment line
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'], 
                  y=daily_sentiment['score'],
                  mode='lines',
                  name='Daily Sentiment',
                  line=dict(color='blue'))
    )
    
    # Add moving averages
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'],
                  y=daily_sentiment['MA3'],
                  mode='lines',
                  name='3-day MA',
                  line=dict(color='green', dash='dot'))
    )
    
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'],
                  y=daily_sentiment['MA7'],
                  mode='lines',
                  name='7-day MA',
                  line=dict(color='red', dash='dot'))
    )
    
    # Add election date line
    election_date = pd.Timestamp('2024-11-05')
    min_y = daily_sentiment['score'].min()
    max_y = daily_sentiment['score'].max()
    
    # Add election date as a shape
    fig.add_shape(
        type="line",
        x0=election_date,
        x1=election_date,
        y0=min_y,
        y1=max_y,
        line=dict(color="red", dash="dash")
    )
    
    # Add election date annotation
    fig.add_annotation(
        x=election_date,
        y=max_y,
        text="Election Day",
        showarrow=False,
        yshift=10
    )
    
    # Update layout
    fig.update_layout(
        height=500,
        title_text="Crypto News Sentiment Trend",
        showlegend=True,
        xaxis_title="Date",
        yaxis_title="Sentiment Score"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show hot topics
    st.subheader("Hot Topics")
    topics = extract_topic_words(df)
    if topics:
        cols = st.columns(len(topics))
        for col, (word, count) in zip(cols, topics):
            col.metric(f"#{word}", count)

if __name__ == "__main__":
    create_dashboard()
