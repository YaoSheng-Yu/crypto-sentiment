import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import json
from datetime import datetime
import plotly.express as px

# Page config
st.set_page_config(
    page_title="Crypto Sentiment Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("Crypto News Sentiment Analysis")

# Load data
def load_data():
    try:
        # Load sentiment scores
        scores_df = pd.read_csv('sentiment_scores.csv')
        scores_df['date'] = pd.to_datetime(scores_df['date'])
        
        # Load latest news
        current_month = datetime.now().strftime('%Y%b')
        news_file = Path(f'data/{current_month}.json')
        if news_file.exists():
            with open(news_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
        else:
            news_data = []
            
        return scores_df, news_data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), []

scores_df, news_data = load_data()

# Dashboard layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Sentiment Analysis Over Time")
    
    if not scores_df.empty:
        # Calculate daily sentiment
        daily_sentiment = scores_df.groupby('date').agg({
            'sentiment': lambda x: (x == 'positive').mean(),
            'confidence': 'mean'
        }).reset_index()
        
        # Create sentiment trend plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_sentiment['date'],
            y=daily_sentiment['sentiment'],
            mode='lines+markers',
            name='Positive Sentiment Ratio',
            line=dict(color='#2ecc71', width=2),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Positive Sentiment Ratio",
            hovermode='x unified',
            plot_bgcolor='white',
            yaxis=dict(
                gridcolor='lightgrey',
                range=[0, 1],
                tickformat='.0%'
            ),
            xaxis=dict(
                gridcolor='lightgrey'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Confidence distribution
        st.subheader("Sentiment Confidence Distribution")
        fig_conf = px.histogram(
            scores_df, 
            x='confidence',
            color='sentiment',
            nbins=30,
            opacity=0.7
        )
        
        fig_conf.update_layout(
            xaxis_title="Confidence Score",
            yaxis_title="Count",
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig_conf, use_container_width=True)
    else:
        st.info("No sentiment data available")

with col2:
    st.subheader("Recent News")
    
    if news_data:
        for article in news_data[:5]:  # Show latest 5 articles
            with st.container():
                st.markdown(f"**{article['title']}**")
                st.markdown(f"*{article['published_at'].split('T')[0]}*")
                if article.get('description'):
                    st.markdown(article['description'])
                st.markdown(f"[Read more]({article['url']})")
                st.markdown("---")
    else:
        st.info("No recent news available")

# Footer
st.markdown("---")
st.markdown("Data updates every 12 hours • Powered by MediaStack API and FinBERT")
