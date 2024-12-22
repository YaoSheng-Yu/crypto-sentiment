import json
import pandas as pd
from transformers import pipeline
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            
        # Initialize sentiment analyzer
        sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        
        # Process each article
        new_scores = []
        for article in articles:
            # Analyze title and description
            title_score = sentiment_analyzer(article['title'])[0]
            desc_score = sentiment_analyzer(article.get('description', ''))[0] if article.get('description') else None
            
            # Calculate overall sentiment
            sentiment = title_score['label']
            score = title_score['score']
            
            if desc_score:
                sentiment = desc_score['label'] if desc_score['score'] > score else sentiment
                score = max(score, desc_score['score'])
            
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
