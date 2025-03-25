import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

class AmazonReviewScraper:
    def __init__(self, product_id, max_pages=10, delay_range=(3, 7)):
        """
        Initialize the Amazon review scraper.
        
        Args:
            product_id (str): Amazon product ID (e.g., 'B0BSHF7WHW')
            max_pages (int): Maximum number of pages to scrape
            delay_range (tuple): Range of seconds to delay between requests
        """
        self.product_id = "B09G9FPHY6"
        self.base_url = f"https://www.amazon.com/product-reviews/{product_id}"
        self.max_pages = max_pages
        self.delay_range = delay_range
        self.reviews = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.amazon.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
    
    def _random_delay(self):
        """Apply a random delay between requests to avoid detection."""
        delay = random.uniform(*self.delay_range)
        logger.info(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
    
    def _fetch_page(self, url):
        """Fetch and parse a page with error handling."""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url)
            
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            elif response.status_code == 503 or response.status_code == 429:
                logger.warning(f"Rate limited (status {response.status_code}). Consider increasing delay.")
                return None
            else:
                logger.error(f"Failed to fetch page: {url} (Status: {response.status_code})")
                return None
        except Exception as e:
            logger.error(f"Exception while fetching {url}: {str(e)}")
            return None
    
    def extract_reviews_from_page(self, soup):
        """Extract review text from a page's soup."""
        if not soup:
            return []
        
        page_reviews = []
        # Try multiple possible selectors as Amazon might change its structure
        selectors = [
            ("div", {"data-hook": "review-collapsed"}),
            ("span", {"data-hook": "review-body"}),
            ("span", {"class": "a-size-base review-text"})
        ]
        
        for tag, attrs in selectors:
            review_elements = soup.find_all(tag, attrs=attrs)
            if review_elements:
                logger.info(f"Found {len(review_elements)} reviews using selector {tag}, {attrs}")
                for element in review_elements:
                    if tag == "div":
                        span = element.find("span")
                        text = span.text.strip() if span else ""
                    else:
                        text = element.text.strip()
                    
                    if text:
                        page_reviews.append(text)
                break
        
        if not page_reviews:
            logger.warning("No reviews found on this page. Amazon may have changed their HTML structure.")
        
        return page_reviews
    
    def find_next_page_url(self, soup):
        """Find the URL for the next page of reviews."""
        if not soup:
            return None
        
        # Method 1: Look for the "Next page" button
        next_page_li = soup.find("li", class_="a-last")
        if next_page_li:
            next_page_a = next_page_li.find("a")
            if next_page_a and next_page_a.get("href"):
                return urljoin("https://www.amazon.com", next_page_a["href"])
        
        # Method 2: Look for pagination
        pagination = soup.find("div", {"id": "cm_cr-pagination_bar"})
        if pagination:
            next_links = pagination.find_all("a", class_="a-link-normal")
            for link in next_links:
                if link.text and "Next" in link.text:
                    return urljoin("https://www.amazon.com", link["href"])
        
        return None
    
    def scrape(self):
        """Main method to scrape reviews across multiple pages."""
        current_url = self.base_url
        page_num = 1
        
        while current_url and page_num <= self.max_pages:
            logger.info(f"Processing page {page_num} of {self.max_pages}")
            
            soup = self._fetch_page(current_url)
            if not soup:
                logger.error(f"Failed to fetch page {page_num}. Stopping.")
                break
            
            page_reviews = self.extract_reviews_from_page(soup)
            self.reviews.extend(page_reviews)
            logger.info(f"Extracted {len(page_reviews)} reviews from page {page_num}")
            
            next_url = self.find_next_page_url(soup)
            if next_url and next_url != current_url:
                current_url = next_url
                page_num += 1
                self._random_delay()  # Delay before next request
            else:
                logger.info("No more pages available or reached last page.")
                break
        
        logger.info(f"Scraping complete. Collected {len(self.reviews)} reviews.")
        return self.reviews

    def save_to_file(self, filename="amazon_reviews.txt"):
        """Save reviews to a text file."""
        with open(filename, "w", encoding="utf-8") as f:
            for i, review in enumerate(self.reviews, 1):
                f.write(f"Review {i}:\n{review}\n\n{'='*50}\n\n")
        logger.info(f"Saved {len(self.reviews)} reviews to {filename}")

# Example usage
if __name__ == "__main__":
    product_id = "B0BSHF7WHW"  # Replace with your Amazon product ID
    scraper = AmazonReviewScraper(product_id, max_pages=10, delay_range=(3, 7))
    reviews = scraper.scrape()
    
    # Print some sample reviews
    for i, review in enumerate(reviews[:5], 1):
        print(f"Review {i}: {review[:100]}...")
    
    # Save all reviews to file
    scraper.save_to_file()