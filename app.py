# Description: This file contains the code for Passivebot's x WordForest's Facebook Marketplace Scraper API. This code was initially authored by Harminder Nijjar and modified by Tanya Da Costa to fit custom Marketplace needs.
# Date: 2024-01-24
# Author: Harminder Nijjar, Tanya Da Costa
# Version: 2.0.0.
# Usage: python app.py

# TODO: favicon

# Import the necessary libraries.
# Playwright is used to crawl the Facebook Marketplace.
from playwright.sync_api import sync_playwright, Page
# The os library is used to get the environment variables.
import os
# The time library is used to add a delay to the script.
import time
# The BeautifulSoup library is used to parse the HTML.
from bs4 import BeautifulSoup
# The FastAPI library is used to create the API.
from fastapi import HTTPException, FastAPI
# The JSON library is used to convert the data to JSON.
import json
# The uvicorn library is used to run the API.
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
# The logging library is used for error logging.
import logging
import traceback
# Threading and queue for Playwright worker
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
                 
# Create an instance of the FastAPI class.
app = FastAPI()
# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Clean up browser resources on app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    shutdown_playwright_worker()
    logger.info("Application shutdown - playwright worker stopped")

# Playwright Worker System to avoid asyncio conflicts
job_queue = queue.Queue()
result_queues = {}
playwright_worker_thread = None
playwright_shutdown_event = threading.Event()

# Global browser variables (managed by worker thread)
browser = None
page = None
playwright_instance = None

def playwright_worker():
    """Dedicated worker thread for all Playwright operations"""
    global browser, page, playwright_instance
    
    logger.info("Playwright worker thread started")
    
    while not playwright_shutdown_event.is_set():
        try:
            # Wait for jobs with timeout to allow clean shutdown
            job = job_queue.get(timeout=1.0)
            job_id = job.get('job_id')
            action = job.get('action')
            
            try:
                if action == 'crawl':
                    # Initialize browser if needed - start in headless mode by default
                    if browser is None or page is None:
                        initialize_browser_worker(headless=True)
                    
                    # Perform the crawl
                    result = crawl_query_worker(
                        job['city'], 
                        job['query'], 
                        job['max_price'], 
                        job['max_results'], 
                        job['suggested']
                    )
                    
                    # Send result back
                    if job_id in result_queues:
                        result_queues[job_id].put({'success': True, 'data': result})
                        
                elif action == 'shutdown':
                    logger.info("Playwright worker received shutdown signal")
                    cleanup_browser_resources_worker()
                    break
                    
            except Exception as e:
                logger.error(f"Error in playwright worker: {e}")
                if job_id in result_queues:
                    result_queues[job_id].put({'success': False, 'error': str(e)})
                
            finally:
                job_queue.task_done()
                
        except queue.Empty:
            continue  # Timeout, check shutdown flag
        except Exception as e:
            logger.error(f"Unexpected error in playwright worker: {e}")
    
    logger.info("Playwright worker thread stopping")

def initialize_browser_worker(headless=True):
    """Initialize browser in worker thread context"""
    global browser, page, playwright_instance
    try:
        if browser is None:
            playwright_instance = sync_playwright().start()
            # Use persistent context to maintain login sessions across crashes
            browser = playwright_instance.chromium.launch_persistent_context(
                user_data_dir="fb_profile",  # Persistent user data directory
                headless=headless,
                args=[
                    '--enable-logging', 
                    '--v=1',
                    '--no-first-run',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            # For persistent context, browser acts as both browser and page context
            # Get the first page or create one if none exists
            if len(browser.pages) > 0:
                page = browser.pages[0]
            else:
                page = browser.new_page()
            headless_status = "headless" if headless else "visible"
            logger.info(f"Browser initialized successfully with persistent context ({headless_status}) in worker thread")
    except Exception as e:
        logger.error(f"Error initializing browser in worker: {e}")
        cleanup_browser_resources_worker()
        raise e

def cleanup_browser_resources_worker():
    """Clean up browser resources in worker thread context"""
    global browser, page, playwright_instance
    try:
        if browser:
            browser.close()
    except Exception as e:
        logger.warning(f"Error closing browser in worker: {e}")
    
    try:
        if playwright_instance:
            playwright_instance.stop()
    except Exception as e:
        logger.warning(f"Error stopping playwright in worker: {e}")
    
    browser = None
    page = None
    playwright_instance = None

def start_playwright_worker():
    """Start the playwright worker thread"""
    global playwright_worker_thread
    if playwright_worker_thread is None or not playwright_worker_thread.is_alive():
        playwright_shutdown_event.clear()
        playwright_worker_thread = threading.Thread(target=playwright_worker, daemon=True)
        playwright_worker_thread.start()
        logger.info("Playwright worker thread started")

def shutdown_playwright_worker():
    """Shutdown the playwright worker thread"""
    global playwright_worker_thread
    if playwright_worker_thread and playwright_worker_thread.is_alive():
        # Signal shutdown
        playwright_shutdown_event.set()
        job_queue.put({'action': 'shutdown'})
        
        # Wait for thread to finish
        playwright_worker_thread.join(timeout=10)
        if playwright_worker_thread.is_alive():
            logger.warning("Playwright worker thread did not shut down cleanly")
        else:
            logger.info("Playwright worker thread shut down successfully")

# Start worker on import
start_playwright_worker()

def login_and_goto_marketplace_worker(initial_url, marketplace_url):
    """Worker thread version of login function - switches to visible mode when login needed"""
    global page, browser
    try:
        if page is None:
            logger.error("Page is None, cannot proceed with login")
            return
            
        page.goto(initial_url)
        time.sleep(2)
        
        # If url does not contain "login", we assume we are logged in and redirect to marketplace
        if "login" not in page.url:
            logger.info("Already logged in, proceeding to marketplace")
            page.goto(marketplace_url)
            return
            
        # Login is required - check if we're running headless and need to switch to visible
        logger.info("Login required - checking browser mode")
        
        # Check if browser is currently headless by trying to detect if we can interact with login
        try:
            # Try to go to Facebook and check if we can see login elements
            page.goto("https://www.facebook.com")
            time.sleep(3)
            
            # Look for login elements
            login_elements = page.locator('input[name="email"], input[data-testid="royal_email"]').count()
            
            if login_elements > 0:
                logger.info("Login form detected - need visible browser for manual login")
                
                # Check if we're running in headless mode
                try:
                    # Try to detect if browser window is visible
                    is_headless = page.evaluate("() => window.outerHeight === 0 || window.outerWidth === 0")
                    if is_headless:
                        logger.info("Currently in headless mode, restarting browser in visible mode for login")
                        cleanup_browser_resources_worker()
                        initialize_browser_worker(headless=False)  # Restart in visible mode
                        page.goto("https://www.facebook.com")
                        time.sleep(3)
                except Exception as detection_error:
                    logger.warning(f"Could not detect browser mode: {detection_error}, assuming headless")
                    # If we can't detect, restart in visible mode to be safe
                    cleanup_browser_resources_worker()
                    initialize_browser_worker(headless=False)
                    page.goto("https://www.facebook.com")
                    time.sleep(3)
                
                # Wait for manual login
                wait_for_user_login(page)
                
                # After successful login, we can continue - browser will stay visible for this session
                logger.info("Login completed successfully")
            
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            # If we can't determine login status, assume login is needed in visible mode
            cleanup_browser_resources_worker()
            initialize_browser_worker(headless=False)
            page.goto("https://www.facebook.com")
            wait_for_user_login(page)
        
        # After login, navigate to marketplace
        page.goto(marketplace_url)
        time.sleep(5)  # Wait for marketplace to load
        
    except Exception as e:
        logger.error(f"Login error in worker: {e}")
        raise e

def restart_browser_worker():
    """Worker thread version of browser restart - starts in headless mode by default"""
    global browser, page
    logger.warning("Restarting browser in worker thread...")
    
    # Clean up existing resources
    cleanup_browser_resources_worker()
    
    # Try to initialize browser once - start headless by default
    try:
        initialize_browser_worker(headless=True)  # Default to headless mode
        logger.info("Browser restarted successfully in worker thread (headless mode)")
    except Exception as e:
        logger.error(f"Failed to restart browser in worker thread: {e}")
        raise e

def wait_for_user_login(page):
    print("Please log in manually in the opened Chromium window...")

    try:
        # Wait for navigation after form submission
        with page.expect_navigation(timeout=600_000):  # wait up to 10 minutes
            # Wait for the login button to appear
            page.wait_for_selector('button[name="login"]')
            print("Login button is available. Waiting for user to submit the form...")

            # Optionally: Wait until button is actually clicked
            page.locator('button[name="login"]').wait_for(state="detached", timeout=600_000)

        print("Login detected, proceeding with scraping...")
    except Exception as e:
        logger.error(f"Error waiting for user login: {e}")
        raise e


# Create a route to the root endpoint.
@app.get("/")
# Define a function to be executed when the endpoint is called.
def root():
    # Return a message.
    return {"message": "Welcome to Passivebot's Facebook Marketplace API. Documentation is currently being worked on along with the API. Some planned features currently in the pipeline are a ReactJS frontend, MongoDB database, and Google Authentication."}

# Create a route to the return_data endpoint.
@app.get("/crawl_facebook_marketplace")
# Define a function to be executed when the endpoint is called.
# Add a description to the function.
# TODO: days since listed input
def crawl_facebook_marketplace(city: str, query: str, max_price: int, max_results_per_query: int):
    # Define dictionary of cities from the facebook marketplace directory for United States.
    # https://m.facebook.com/marketplace/directory/US/?_se_imp=0oey5sMRMSl7wluQZ
    cities = {
        'Hamilton': 'hamilton',  # TODO: more Ontario cities
        'Barrie': 'barrie',
        'Toronto': 'toronto'
    }
    # If the city is in the cities dictionary...
    if city in cities:
        # Get the city location id from the cities dictionary.
        city = cities[city]
    # If the city is not in the cities dictionary...
    else:
        # Exit the script if the city is not in the cities dictionary.
        # Capitalize only the first letter of the city.
        city = city.capitalize()
        # Raise an HTTPException.
        raise HTTPException (404, f'{city} is not a city we are currently supporting on the Facebook Marketplace. Please reach out to us to add this city in our directory.')
        
    # Define the URL to scrape.
    results = []
    # Split the query into a list
    query_list = query.split(',')
    for query in query_list:
      try:
        # Use the new robust crawling method
        recent_query_results = crawl_query(city, query, max_price, max_results_per_query, False)
        suggested_results = crawl_query(city, query, max_price, max_results_per_query, True)
      except Exception as e:
        logger.error(f"Error crawling query '{query}': {e}")
        recent_query_results = []
        suggested_results = []

      recent_query_results_urls = [item["link"] for item in recent_query_results]
      suggested_results_urls = [item["link"] for item in suggested_results]

      # If the items appear in both recent and suggested, mark them as "hot"
      common_items = set(recent_query_results_urls) & set(suggested_results_urls)
      logger.info(f"Common item links for query '{query}': {list(common_items)}")

      # Add metadata to indicate item type based on new requirements:
      # - "NEW" pill: only for recent results with "just listed" pill
      # - "HOT" pill: only for suggested results with "just listed" pill  
      # - "SUGGESTED" pill: for suggested results without "just listed" pill
      # - No special pill: for recent results without "just listed" pill
      
      for item in recent_query_results:
        if item.get('has_just_listed_pill', False):
          item["item_type"] = "new"  # Recent with "just listed" pill
        else:
          item["item_type"] = "recent"  # Recent without "just listed" pill

      for item in suggested_results:
        if item.get('has_just_listed_pill', False):
          item["item_type"] = "hot"  # Suggested with "just listed" pill (hot item)
        else:
          item["item_type"] = "suggested"  # Suggested without "just listed" pill

      consolidated_query_result_urls = list(common_items) + [item for item in recent_query_results_urls + suggested_results_urls if item not in list(common_items)]
      consolidated_query_results = [item for item in recent_query_results + suggested_results if item["link"] in consolidated_query_result_urls]

      results.extend(consolidated_query_results)

    return results

if __name__ == "__main__":

    # Run the app.
    uvicorn.run(
        # Specify the app as the FastAPI app.
        'app:app',
        host='127.0.0.1',
        port=8000
    )

def crawl_query(city: str, query: str, max_price: int, max_results: int, suggested: bool):
    """Submit crawl job to worker thread and wait for result"""
    job_id = str(uuid.uuid4())
    result_queue = queue.Queue()
    result_queues[job_id] = result_queue
    
    try:
        # Submit job to worker thread
        job = {
            'job_id': job_id,
            'action': 'crawl',
            'city': city,
            'query': query,
            'max_price': max_price,
            'max_results': max_results,
            'suggested': suggested
        }
        
        job_queue.put(job)
        
        # Wait for result with timeout
        try:
            result = result_queue.get(timeout=120)  # 2 minute timeout
            if result['success']:
                return result['data']
            else:
                logger.error(f"Crawl failed: {result['error']}")
                return []
        except queue.Empty:
            logger.error("Crawl job timed out")
            return []
            
    finally:
        # Clean up result queue
        if job_id in result_queues:
            del result_queues[job_id]

def crawl_query_worker(city: str, query: str, max_price: int, max_results: int, suggested: bool):
    """Actual crawl implementation running in worker thread"""
    global page
    try:
        marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=1&sortBy=creation_time_descend'
        initial_url = "https://www.facebook.com/login/device-based/regular/login/"
        if suggested:
            marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=3'

        login_and_goto_marketplace_worker(initial_url, marketplace_url)
        
        # Get listings of particular item in a particular city for a particular price.
        # Wait for the page to load.
        time.sleep(5)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        parsed = []
        
        # More robust approach: Use multiple selectors as fallbacks
        listings = find_marketplace_listings(soup)

        for listing in listings:
            # Get the item image using multiple strategies
            image = find_listing_image(listing)
            
            # Get the item title using multiple strategies
            title = find_listing_title(listing)

            # Get the item URL using multiple strategies
            post_url = find_listing_url(listing)

            # Check if listing has "Just listed" pill
            has_just_listed_pill = find_just_listed_pill(listing)

            # Only add the item if the title includes any of the query terms
            query_parts = query.split(' ')
            if title is not None and post_url is not None and image is not None and any(part.lower() in title.lower() for part in query_parts):
                # Append the parsed data to the list.
                parsed.append({
                    'image': image,
                    'title': title,
                    'post_url': post_url,
                    'has_just_listed_pill': has_just_listed_pill
                })

        # Return the parsed data as a JSON.
        result = []
        # Grab only max results amount
        parsed = parsed[:max_results]
        for item in parsed:
            # Determine item type based on suggested flag and "just listed" pill
            if suggested and item['has_just_listed_pill']:
                item_type = 'hot'  # 🔥 HOT items: Suggested results with "Just listed" pill
            elif not suggested and item['has_just_listed_pill']:
                item_type = 'new'  # ✨ NEW items: Recent results with "Just listed" pill
            elif suggested and not item['has_just_listed_pill']:
                item_type = 'suggested'  # 💡 SUGGESTED items: Suggested results without "Just listed" pill
            else:
                item_type = 'recent'  # No badge: Recent results without "Just listed" pill
            
            result.append({
                'name': item['title'],
                'title': item['title'],
                'image': item['image'],
                'link': item['post_url'],
                'has_just_listed_pill': item['has_just_listed_pill'],
                'item_type': item_type
            })

        return result
    except Exception as e:
        logger.error(f"Error during crawl in worker: {e}")
        # Try to restart browser in worker thread
        try:
            restart_browser_worker()
        except Exception as restart_error:
            logger.error(f"Failed to restart browser in worker: {restart_error}")
        return []  # Return empty results instead of crashing

def crawl_query_with_playwright(city: str, query: str, max_price: int, max_results: int, suggested: bool):
    """Alternative approach - now also uses worker thread system"""
    # This function now just calls the main crawl_query which uses the worker
    return crawl_query(city, query, max_price, max_results, suggested)

def find_marketplace_listings(soup):
    """Find marketplace listings using multiple strategies."""
    # Strategy 1: Look for divs that contain both an image and a link (common marketplace pattern)
    listings = soup.find_all('div', lambda value: value and len(value.split()) > 10)  # Divs with many classes
    
    # Filter to only divs that contain both an image and a link
    marketplace_listings = []
    for listing in listings:
        has_image = listing.find('img') is not None
        has_link = listing.find('a') is not None
        if has_image and has_link:
            marketplace_listings.append(listing)
    
    # Strategy 2: If no listings found, try a broader search
    if not marketplace_listings:
        # Look for any div containing marketplace-like content
        all_divs = soup.find_all('div')
        for div in all_divs:
            img = div.find('img')
            link = div.find('a')
            if img and link and img.get('src') and link.get('href'):
                # Check if the link looks like a marketplace item
                href = link.get('href', '')
                if '/marketplace/item/' in href or 'marketplace' in href:
                    marketplace_listings.append(div)
    
    # Fallback: Use configurable selectors to find listings
    if not marketplace_listings and 'FALLBACK_SELECTORS' in globals():
        for selector in FALLBACK_SELECTORS['listings']:
            listings = soup.select(selector)
            for listing in listings:
                if listing not in marketplace_listings:
                    marketplace_listings.append(listing)
            if marketplace_listings:
                break
    
    return marketplace_listings

def find_listing_image(listing):
    """Find the image URL using multiple strategies."""
    # Strategy 1: Look for any img tag with src
    img_tags = listing.find_all('img')
    for img in img_tags:
        src = img.get('src')
        if src and ('facebook' in src or 'fbcdn' in src or src.startswith('https://')):
            return src
    
    # Strategy 2: Look for img with alt text or specific attributes
    img_with_alt = listing.find('img', attrs={'alt': True})
    if img_with_alt and img_with_alt.get('src'):
        return img_with_alt.get('src')
    
    # Fallback: Use configurable selectors to find images
    if 'FALLBACK_SELECTORS' in globals():
        for selector in FALLBACK_SELECTORS['images']:
            img = listing.select_one(selector)
            if img and img.get('src'):
                return img.get('src')
    
    return None

def find_listing_title(listing):
    """Find the listing title using multiple strategies."""
    # Strategy 1: Look for span elements with text content
    spans = listing.find_all('span')
    for span in spans:
        text = span.get_text(strip=True)
        if text and len(text) > 5 and len(text) < 200:  # Reasonable title length
            # Skip common UI elements
            if not any(skip in text.lower() for skip in ['$', 'price', 'location', 'see more', 'show more']):
                return text
    
    # Strategy 2: Look for any text in links
    links = listing.find_all('a')
    for link in links:
        text = link.get_text(strip=True)
        if text and len(text) > 5 and len(text) < 200:
            return text
    
    # Strategy 3: Look for divs with text content
    divs = listing.find_all('div')
    for div in divs:
        text = div.get_text(strip=True)
        if text and len(text) > 5 and len(text) < 200:
            # Make sure it's not a nested element with lots of content
            if len(div.find_all()) < 3:
                return text
    
    # Fallback: Use configurable selectors to find titles
    if 'FALLBACK_SELECTORS' in globals():
        for selector in FALLBACK_SELECTORS['titles']:
            title_element = listing.select_one(selector)
            if title_element and title_element.get_text(strip=True):
                return title_element.get_text(strip=True)
    
    return None

def find_listing_url(listing):
    """Find the listing URL using multiple strategies."""
    # Strategy 1: Look for links that go to marketplace items
    links = listing.find_all('a')
    for link in links:
        href = link.get('href')
        if href:
            # Make sure it's a marketplace item link
            if '/marketplace/item/' in href or 'marketplace' in href:
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = 'https://www.facebook.com' + href
                return href
    
    # Strategy 2: Look for any link that might be the main item link
    for link in links:
        href = link.get('href')
        if href and href.startswith('https://www.facebook.com'):
            return href
    
    # Fallback: Use configurable selectors to find links
    if 'FALLBACK_SELECTORS' in globals():
        for selector in FALLBACK_SELECTORS['links']:
            link_element = listing.select_one(selector)
            if link_element and link_element.get('href'):
                href = link_element.get('href')
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = 'https://www.facebook.com' + href
                return href
    
    return None

def find_just_listed_pill(listing):
    """Find the 'Just listed' pill on Facebook Marketplace listings."""
    # Strategy 1: Look for text that contains "just listed" variations
    all_text_elements = listing.find_all(text=True)
    for text in all_text_elements:
        text_lower = text.strip().lower()
        if text_lower in ['just listed', 'just now', 'new listing', 'recently listed']:
            return True
    
    # Strategy 2: Look for specific elements that might contain the pill
    # Facebook often uses span or div elements for pills/badges
    spans = listing.find_all('span')
    for span in spans:
        span_text = span.get_text(strip=True).lower()
        if span_text in ['just listed', 'just now', 'new listing', 'recently listed']:
            return True
    
    # Strategy 3: Look for divs with pill-like styling or content
    divs = listing.find_all('div')
    for div in divs:
        div_text = div.get_text(strip=True).lower()
        if div_text in ['just listed', 'just now', 'new listing', 'recently listed']:
            # Check if this div looks like a pill (small, styled element)
            if len(div_text) < 20 and not div.find_all(['img', 'a']):  # Likely a text pill
                return True
    
    # Strategy 4: Look for elements with common pill/badge class patterns
    # Facebook might use classes like 'pill', 'badge', 'tag', etc.
    pill_elements = listing.find_all(attrs={'class': lambda x: x and any(keyword in ' '.join(x).lower() for keyword in ['pill', 'badge', 'tag', 'label'])})
    for element in pill_elements:
        element_text = element.get_text(strip=True).lower()
        if any(keyword in element_text for keyword in ['just', 'listed', 'new', 'recent']):
            return True
    
    return False

# Configuration for fallback selectors (can be updated if needed)
FALLBACK_SELECTORS = {
    'listings': [
        'div[role="article"]',
        'div[data-testid*="marketplace"]',
        'div:has(img):has(a[href*="marketplace"])',
        # Add more fallback selectors as needed
    ],
    'images': [
        'img[src*="fbcdn"]',
        'img[src*="facebook"]',
        'img[alt]',
    ],
    'links': [
        'a[href*="/marketplace/item/"]',
        'a[href*="marketplace"]',
        'a[role="link"]',
    ],
    'titles': [
        'span:not(:empty)',
        'div:not(:empty)',
        'h1, h2, h3, h4, h5, h6',
    ]
}

