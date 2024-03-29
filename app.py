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
        'Hamilton': 'hamilton'  # TODO: more oNTARIO cities
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
      recent_query_results = crawl_query(city, query, max_price, max_results_per_query, False)
      suggested_results =  crawl_query(city, query, max_price, max_results_per_query, True)

      print("suggested. do these show up in the results read out?")
      print(suggested_results)

      recent_query_results_urls = [item["link"] for item in recent_query_results]
      suggested_results_urls = [item["link"] for item in suggested_results]

      # If the items appear in both recent and suggested, put them in the top of the list
      common_items = set(recent_query_results_urls) & set(suggested_results_urls)

      consolidated_query_result_urls = list(common_items) + [item for item in recent_query_results_urls + suggested_results_urls if item not in list(common_items)]
      consolidated_query_results = [item for item in recent_query_results + suggested_results if item["link"] in consolidated_query_result_urls]

      print("consolidated") # TODO: FUCKING CONSolidated is missing suggested. oh.copy pasta bug
      print(consolidated_query_results)
      results.extend(consolidated_query_results)

    return results

# Create a route to the return_html endpoint.
@app.get("/return_ip_information")
# Define a function to be executed when the endpoint is called.
def return_ip_information():
    # Initialize the session using Playwright.
    with sync_playwright() as p:
        # Open a new browser page.
        browser = p.chromium.launch()
        page = browser.new_page()
        # Navigate to the URL.
        page.goto('https://www.ipburger.com/')
        # Wait for the page to load.
        time.sleep(5)
        # Get the HTML content of the page.
        html = page.content()
        # Beautify the HTML content.
        soup = BeautifulSoup(html, 'html.parser')
        # Find the IP address.
        ip_address = soup.find('span', id='ipaddress1').text
        # Find the country.
        country = soup.find('strong', id='country_fullname').text
        # Find the location.
        location = soup.find('strong', id='location').text
        # Find the ISP.
        isp = soup.find('strong', id='isp').text
        # Find the Hostname.
        hostname = soup.find('strong', id='hostname').text
        # Find the Type.
        ip_type = soup.find('strong', id='ip_type').text
        # Find the version.
        version = soup.find('strong', id='version').text
        # Return the IP information as JSON.
        return {
            'ip_address': ip_address,
            'country': country,
            'location': location,
            'isp': isp,
            'hostname': hostname,
            'type': ip_type,
            'version': version
        }

if __name__ == "__main__":

    # Run the app.
    uvicorn.run(
        # Specify the app as the FastAPI app.
        'app:app',
        host='127.0.0.1',
        port=8000
    )

def crawl_query(city: str, query: str, max_price: int, max_results: int, suggested: bool):
    # TODO: sometimes facebook asks us to login. need to get login back but with persisting session cookies. Or figure out how to close the modal (nvm we can still scrape with the modal open)
    marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=1&sortBy=creation_time_descend'
    if suggested:
      marketplace_url = f'https://www.facebook.com/marketplace/{city}/search?query={query}&maxPrice={max_price}&daysSinceListed=3'
    # Get listings of particular item in a particular city for a particular price.
    # Initialize the session using Playwright.
    with sync_playwright() as p:
      # Open a new browser page.
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()
      page.goto(marketplace_url) # TODO: crash is due to timeout here. try catch?

      # Wait for the page to load.
      time.sleep(5)
      html = page.content()
      soup = BeautifulSoup(html, 'html.parser')
      parsed = []
      listings = soup.find_all('div', class_='x9f619 x78zum5 x1r8uery xdt5ytf x1iyjqo2 xs83m0k x1e558r4 x150jy0e x1iorvi4 xjkvuk6 xnpuxes x291uyu x1uepa24')
      # Grab the latest lists
      latest_listings = listings[:max_results]

      for listing in latest_listings:
            # Get the item image.
            image = listing.find('img', class_='xt7dq6l xl1xv1r x6ikm8r x10wlt62 xh8yej3')
            if image is not None:
              image = image['src']

            # TODO: better way to grab these or move these classes to config. They change sometimes
            # Get the item title from span.
            title = listing.find('span', 'x1lliihq x6ikm8r x10wlt62 x1n2onr6')
            if title is not None:
              title = title.text

            # Get the item URL.
            post_url = listing.find('a', class_='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g x1lku1pv')
            if post_url is not None:
              post_url = post_url['href']
            
            if title is not None and post_url is not None and image is not None:
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

