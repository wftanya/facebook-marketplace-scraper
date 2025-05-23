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

# Global variables for the browser and page
browser = None
page = None

def initialize_browser():
    global browser, page
    try:
      if browser is None:
          playwright = sync_playwright().start()
          browser = playwright.chromium.launch(headless=False, args=['--enable-logging', '--v=1'])
          page = browser.new_page()
    except Exception as e:
      logger.error(f"Error initializing browser: {e}")
      restart_browser()

def login_and_goto_marketplace(initial_url, marketplace_url):
    global page
    page.goto(initial_url)
    time.sleep(2)
    try:
      # If url does not contain "login", we assume we are logged in and redirect to marketplace
      if "login" not in page.url:
          page.goto(marketplace_url)
          return
      # If not logged in, go to Facebook homepage and wait for manual login
      page.goto("https://www.facebook.com")
      wait_for_user_login(page)
      
      # After login, navigate to marketplace
      page.goto(marketplace_url)
      time.sleep(5)  # Wait for marketplace to load
        
    except Exception as e:
      logger.error(f"Login error: {e}")
      restart_browser()

def wait_for_user_login(page):
    st.info("Please log in manually in the opened Chromium window...")
    print("Please login manually in the browser window...")

    # Wait for navigation after form submission
    with page.expect_navigation(timeout=600_000):  # wait up to 10 minutes
        # Wait for the login button to appear
        page.wait_for_selector('button[name="login"]')
        print("Login button is available. Waiting for user to submit the form...")

        # Optionally: Wait until button is actually clicked
        page.locator('button[name="login"]').wait_for(state="detached", timeout=600_000)

    print("Login detected, proceeding with scraping...")
    # TODO: this is not automatically going to marketplace, have to hit force run again.
    # If we can't get it auto redirecting we should just have a separate login button
 
def goto_marketplace(marketplace_url):
    page.goto(marketplace_url)

def restart_browser():
    global browser, page
    logger.warning("Restarting the browser due to crash or failure...")
    if browser:
        browser.close()
    browser = None
    initialize_browser()


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
        # TODO: umm it seems to only consider the query the first time around? Or is that because im not signing in anymore?
        recent_query_results = crawl_query(city, query, max_price, max_results_per_query, False)
        suggested_results =  crawl_query(city, query, max_price, max_results_per_query, True)
      except:
        recent_query_results = []
        suggested_results = []

      recent_query_results_urls = [item["link"] for item in recent_query_results]
      suggested_results_urls = [item["link"] for item in suggested_results]

      # If the items appear in both recent and suggested, put them in the top of the list
      common_items = set(recent_query_results_urls) & set(suggested_results_urls)

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
  global page
  try:
    marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=1&sortBy=creation_time_descend'
    initial_url = "https://www.facebook.com/login/device-based/regular/login/"
    if suggested:
      marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=3'

    # Initialize browser if not already initialized
    initialize_browser()

    login_and_goto_marketplace(initial_url, marketplace_url)
    # goto_marketplace(marketplace_url) # TODO: if login captcha locked.. comment above and uncomment this

    # Get listings of particular item in a particular city for a particular price.
    # Wait for the page to load.
    time.sleep(5)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    parsed = []
    listings = soup.find_all('div', class_='x9f619 x78zum5 x1r8uery xdt5ytf x1iyjqo2 xs83m0k x1e558r4 x150jy0e x1iorvi4 xjkvuk6 xnpuxes x291uyu x1uepa24')

    for listing in listings:
      # Get the item image.
      image = listing.find('img', class_='x168nmei x13lgxp2 x5pf9jr xo71vjh xt7dq6l xl1xv1r x6ikm8r x10wlt62 xh8yej3')
      if image is not None:
        image = image['src']

      # TODO: better way to grab these or move these classes to config. They change sometimes
      # Get the item title from span.
      title = listing.find('span', 'x1lliihq x6ikm8r x10wlt62 x1n2onr6')
      if title is not None:
        title = title.text

      # Get the item URL.
      post_url = listing.find('a', class_='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g xkrqix3 x1sur9pj x1s688f x1lku1pv')
      if post_url is not None:
        post_url = post_url['href']

      # Only add the item if the title includes any of the query terms
      query_parts = query.split(' ')
      if title is not None and post_url is not None and image is not None and any(part.lower() in title.lower() for part in query_parts):
        # Append the parsed data to the list.
        parsed.append({
            'image': image,
            # 'location': location,
            'title': title,
            # 'price': price,
            'post_url': post_url
        })

    # Return the parsed data as a JSON.
    # TODO: put in a dict for query headings
    result = []
    # Grab only max results amount
    parsed = parsed[:max_results]
    for item in parsed:
        result.append({
            'name': item['title'],
            # 'price': item['price'],
            # 'location': item['location'],
            'title': item['title'],
            'image': item['image'],
            'link': item['post_url']
        })

    return result
  except Exception as e:
    logger.error(f"Error during crawl: {e}")
    restart_browser()  # Restart on failure

