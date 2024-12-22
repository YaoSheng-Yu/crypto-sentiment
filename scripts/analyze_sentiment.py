import json
import pandas as pd
from textblob import TextBlob
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_sentiment(text):
    analysis = TextBlob(text)
    # Convert polarity to our sentiment categories
    if analysis.sentiment.polarity > 0.1:
        return 'positive', abs(analysis.sentiment.polarity)
    elif analysis.sentiment.polarity < -0.1:
        return 'negative', abs(analysis.sentiment.polarity)
    else:
        return 'neutral', abs(analysis.sentiment.polarity)

def analyze_new_articles():
    try:
        # Load articles from temp.json
        temp_file = Path('data/temp.json')
        if not temp_file.exists():
            logging.info("No new articles to analyze")
            return
            
        with open(temp_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        if not articles:
            logging.info("No articles found in temp.json")
            return
            
        # Process each article
        new_scores = []
        for article in articles:
            # Analyze title and description
            title_sentiment, title_score = get_sentiment(article['title'])
            desc_sentiment, desc_score = get_sentiment(article.get('description', '')) if article.get('description') else (None, 0)
            
            # Use the stronger sentiment
            if desc_score > title_score:
                sentiment = desc_sentiment
                score = desc_score
            else:
                sentiment = title_sentiment
                score = title_score
            
            # Create score entry
            new_scores.append({
                'date': article['published_at'].split('T')[0],
                'title': article['title'],
                'url': article['url'],
                'sentiment': sentiment,
                'confidence': score
            })
        
        # Load existing scores or create new DataFrame
        scores_file = Path('sentiment_scores.csv')
        if scores_file.exists():
            df = pd.read_csv(scores_file)
        else:
            df = pd.DataFrame(columns=['date', 'title', 'url', 'sentiment', 'confidence'])
        
        # Add new scores
        new_df = pd.DataFrame(new_scores)
        df = pd.concat([new_df, df], ignore_index=True)
        
        # Save updated scores
        df.to_csv(scores_file, index=False)
        logging.info(f"Added {len(new_scores)} new sentiment scores")
        
        # Clean up temp file
        os.remove(temp_file)
        
    except Exception as e:
        logging.error(f"Error in sentiment analysis: {e}")
        raise

if __name__ == "__main__":
    analyze_new_articles()
