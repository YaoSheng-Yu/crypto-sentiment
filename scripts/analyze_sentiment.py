import json
import pandas as pd
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import torch
import os
from datetime import datetime

def analyze_new_articles():
    """Analyze sentiment of new articles from temp.json and append to sentiment_scores.csv"""
    
    # Check if temp.json exists
    if not os.path.exists('data/temp.json'):
        print("No new articles to analyze")
        return
    
    # Load new articles
    with open('data/temp.json', 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    if not articles:
        print("No new articles to analyze")
        return
    
    # Initialize FinBERT
    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    finbert = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)
    
    # Initialize RoBERTa for verification
    roberta_sentiment = pipeline("sentiment-analysis", model="siebert/sentiment-roberta-large-english")
    
    # Load crypto lexicon
    with open('crypto_lexicon.json', 'r') as f:
        crypto_lexicon = json.load(f)
    
    results = []
    for article in articles:
        # Combine title and content for analysis
        text = f"{article['title']} {article['description']}" if article['description'] else article['title']
        
        # FinBERT sentiment
        finbert_result = finbert(text)[0]
        score = {'positive': 1, 'negative': -1, 'neutral': 0}[finbert_result['label']]
        confidence = finbert_result['score']
        
        # Apply crypto lexicon boost
        lexicon_score = sum(crypto_lexicon.get(word.lower(), 0) 
                          for word in text.split() 
                          if word.lower() in crypto_lexicon)
        
        # Combine scores
        final_score = score * confidence + lexicon_score
        
        # Verify very negative scores with RoBERTa
        if final_score < -0.7:
            roberta_result = roberta_sentiment(text)[0]
            if roberta_result['label'] == 'POSITIVE':
                final_score = final_score * 0.5  # Reduce negative sentiment
        
        # Aesthetic scaling
        if abs(final_score) >= 0.8:
            final_score *= 0.8
        elif abs(final_score) >= 0.5:
            final_score *= 0.9
        
        results.append({
            'date': pd.to_datetime(article['published_at']).strftime('%Y-%m-%d'),
            'title': article['title'],
            'url': article['url'],
            'score': final_score
        })
    
    # Load existing scores
    try:
        df_existing = pd.read_csv('data/sentiment_scores.csv')
    except FileNotFoundError:
        df_existing = pd.DataFrame(columns=['date', 'title', 'url', 'score'])
    
    # Create DataFrame for new results
    df_new = pd.DataFrame(results)
    
    # Append new results
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    
    # Save updated scores
    df_combined.to_csv('data/sentiment_scores.csv', index=False)
    
    # Delete temp.json
    os.remove('data/temp.json')
    
    print(f"Added {len(results)} new sentiment scores")

if __name__ == "__main__":
    analyze_new_articles()
