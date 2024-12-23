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

# Add cache with TTL of 5 minutes
@st.cache_data(ttl=300)
def load_and_process_data():
    """Load and process sentiment data from local file"""
    try:
        # Read local CSV file
        df = pd.read_csv('sentiment_scores.csv')
        
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
    if len(sentiment_df) < 2:
        return "NEUTRAL", 50, "Not enough data for trend analysis"
        
    # Get current sentiment score
    current_sentiment = sentiment_df['score'].iloc[-1]
    
    # Calculate trends using the last two values
    ma3_current = sentiment_df['MA3'].iloc[-1]
    ma7_current = sentiment_df['MA7'].iloc[-1]
    ma7_prev = sentiment_df['MA7'].iloc[-2]
    
    short_trend = ma3_current - ma7_current
    medium_trend = ma7_current - ma7_prev
    
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
            ma3_value = daily_sentiment['MA3'].iloc[-1]
            ma7_value = daily_sentiment['MA7'].iloc[-1]
            st.markdown(f"""
            <div style='margin-bottom: 12px; color: {"green" if ma3_value > 0 else "red"}'>{ma3_value:.3f}</div>
            <div style='margin-bottom: 12px; color: {"green" if ma7_value > 0 else "red"}'>{ma7_value:.3f}</div>
            """, unsafe_allow_html=True)
    
    # Recent Articles
    with col3:
        st.subheader("Recent Articles")
        recent_df = df.sort_values('date', ascending=False).head(5)
        for _, row in recent_df.iterrows():
            sentiment_emoji = "🟢" if row['score'] > 0.1 else "🔴" if row['score'] < -0.1 else "⚪"
            # Clean and format the title
            title = row['title']
            # Fix parentheses spacing
            title = re.sub(r'\(\s*', ' (', title)
            title = re.sub(r'\s*\)', ') ', title)
            # Remove any vertical spacing or special characters
            title = re.sub(r'[\n\r\t\f\v]', ' ', title)
            # Fix multiple spaces
            title = re.sub(r'\s+', ' ', title)
            # Clean up any remaining special characters
            title = re.sub(r'[^\w\s\(\),\$\.-]', '', title)
            title = title.strip()
            
            st.markdown(f"{sentiment_emoji} {title}  \n*{row['date'].strftime('%Y-%m-%d')} • Sentiment: {row['score']:.3f}*")
    
    # Main Chart
    st.markdown("---")
    st.subheader("Sentiment Trend Analysis")
    
    fig = make_subplots(rows=1, cols=1)
    
    # Sentiment line
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'], 
                  y=daily_sentiment['score'],
                  mode='lines',
                  name='Daily Sentiment',
                  line=dict(color='gray', width=1))
    )
    
    # Moving averages
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'],
                  y=daily_sentiment['MA3'],
                  mode='lines',
                  name='3-Day MA',
                  line=dict(color='blue', width=2))
    )
    
    fig.add_trace(
        go.Scatter(x=daily_sentiment['date'],
                  y=daily_sentiment['MA7'],
                  mode='lines',
                  name='7-Day MA',
                  line=dict(color='orange', width=2))
    )
    
    # Add election day vertical line (November 7, 2024)
    fig.add_shape(
        type="line",
        x0="2024-11-07",
        x1="2024-11-07",
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=1, dash="dash")
    )
    
    # Add election day annotation
    fig.add_annotation(
        x="2024-11-07",
        y=1,
        yref="paper",
        text="Election Day",
        showarrow=False,
        yshift=10
    )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        plot_bgcolor='white',
        margin=dict(t=0),
        yaxis=dict(title='Sentiment Score',
                  gridcolor='lightgray',
                  zerolinecolor='lightgray'),
        xaxis=dict(title='Date',
                  gridcolor='lightgray'),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Alerts
    alerts = create_alerts(daily_sentiment)
    if alerts:
        st.markdown("### ⚠️ Alerts")
        for alert in alerts:
            st.warning(alert)
    
    # Hot Topics
    st.markdown("---")
    st.subheader("Hot Topics (Last 7 Days)")
    topics = extract_topic_words(df)
    if topics:
        cols = st.columns(5)
        for i, (word, count) in enumerate(topics):
            with cols[i]:
                st.markdown(f"**{word}**  \n{count} mentions")
    else:
        st.write("No topics found")
    
    # Footer
    st.markdown("---")
    st.markdown("Data updates every 12 hours • Powered by TextBlob and MediaStack API")

if __name__ == "__main__":
    create_dashboard()
