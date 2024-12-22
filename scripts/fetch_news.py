import os
import json
from datetime import datetime, timedelta, timezone
import requests
import logging
from pathlib import Path
import unicodedata
import html
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_text(text):
    """Only keep alphanumeric and basic punctuation"""
    if not text:
        return text
    
    # Keep only alphanumeric and these symbols: .,!?-$%()
    cleaned = re.sub(r'[^a-zA-Z0-9\s.,!?$%()\-]', '', text)
    return cleaned.strip()

class NewsManager:
    def __init__(self):
        self.api_key = '7eb65cde9504f2206c3ead3c589ef541'
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        self.base_url = "http://api.mediastack.com/v1/news"

    def get_latest_article_date(self, current_month_file):
        """Get the most recent article date from the current month's file"""
        try:
            if current_month_file.exists():
                with open(current_month_file, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                    if articles:
                        # Assuming articles are sorted by date
                        latest_date = articles[0].get('published_at')
                        if latest_date:
                            return datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
        except Exception as e:
            logging.error(f"Error reading latest article date: {e}")
        
        # If no valid date found, return 24 hours ago
        return datetime.now(timezone.utc) - timedelta(hours=24)

    def get_existing_articles(self, file_path):
        """Get existing articles from monthly file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error reading existing articles: {e}")
        return []

    def fetch_news(self, from_date, to_date, limit=10, sort='popularity'):
        """Fetch news from MediaStack API"""
        params = {
            'access_key': self.api_key,
            'keywords': 'crypto, bitcoin',
            'languages': 'en',
            'sort': sort,
            'limit': limit,
            'date': f"{from_date},{to_date}",
        }
        
        try:
            logging.info(f"Making API request with params: {params}")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Log the API response
            if 'error' in data:
                logging.error(f"API Error: {data['error']}")
                return None
                
            articles = data.get('data', [])
            logging.info(f"API returned {len(articles)} articles")
            
            if articles:
                # Get existing articles to check for duplicates
                monthly_file = self.data_dir / f"{datetime.now(timezone.utc).year}{datetime.now(timezone.utc).strftime('%b')}.json"
                existing_articles = self.get_existing_articles(monthly_file)
                existing_content = {(article['title'].strip().lower(), article['url'].strip().lower()) 
                                 for article in existing_articles}
                
                # Process articles and limit to 5 newest
                processed_articles = []
                seen_content = set()  # Track both title and URL to avoid duplicates
                
                for article in articles:
                    if len(processed_articles) >= 5:  # Stop after 5 articles
                        break
                        
                    if article.get('url') and article.get('title'):
                        title = article.get('title', '').strip().lower()
                        url = article.get('url', '').strip().lower()
                        content_key = (title, url)
                        
                        # Check if article is new (not in existing articles and not a duplicate in current batch)
                        if content_key not in existing_content and content_key not in seen_content:
                            seen_content.add(content_key)
                            processed_articles.append({
                                'title': article.get('title', '').strip(),
                                'description': article.get('description', '').strip(),
                                'url': article.get('url', '').strip(),
                                'source': {'name': article.get('source', '')},
                                'published_at': article.get('published_at', '')
                            })
                
                if processed_articles:
                    # Save new articles to temp.json
                    temp_filename = self.data_dir / 'temp.json'
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        json.dump(processed_articles, f, indent=4, ensure_ascii=False)
                    logging.info(f"Saved {len(processed_articles)} new unique articles to temp.json")
                    
                    # Update monthly file first
                    self.update_monthly_file(monthly_file)
                    
                    # Then trigger sentiment analysis
                    from analyze_new import analyze_new_articles
                    analyze_new_articles()
                    
                    return data
                else:
                    logging.info("No new unique articles found")
                    return None
            else:
                logging.info("No articles found")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching news: {e}")
            return None

    def update_monthly_file(self, file_path):
        """Update monthly file with new articles"""
        temp_file = self.data_dir / 'temp.json'
        if not temp_file.exists():
            logging.info("No temp.json file found")
            return
        
        try:
            # Read new articles from temp.json
            with open(temp_file, 'r', encoding='utf-8') as f:
                new_articles = json.load(f)
            
            if not new_articles:
                logging.info("No new articles to add")
                return
            
            logging.info(f"Found {len(new_articles)} new articles to add")
            
            # Read existing articles
            existing_articles = []
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_articles = json.load(f)
                logging.info(f"Found {len(existing_articles)} existing articles")
            
            # Add new articles at the beginning
            updated_articles = new_articles + existing_articles
            logging.info(f"Total articles after merge: {len(updated_articles)}")
            
            # Save updated articles
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_articles, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Successfully updated {file_path.name} with {len(new_articles)} new articles")
            
        except Exception as e:
            logging.error(f"Error updating monthly file: {e}")
            import traceback
            logging.error(traceback.format_exc())

def main():
    news_manager = NewsManager()
    
    # Get current date
    current_date = datetime.now(timezone.utc)
    json_file = f"{current_date.year}{current_date.strftime('%b')}.json"
    file_path = news_manager.data_dir / json_file
    
    # Get latest article date
    latest_date = news_manager.get_latest_article_date(file_path)
    
    # Format dates for API
    from_date = latest_date.strftime('%Y-%m-%d')
    to_date = current_date.strftime('%Y-%m-%d')
    
    logging.info(f"Fetching news from {from_date} to {to_date}")
    
    # Fetch and process news
    if news_manager.fetch_news(from_date, to_date, limit=10):
        logging.info("Fetch and updates completed successfully")
    else:
        logging.error("Failed to fetch articles")

if __name__ == "__main__":
    main()
