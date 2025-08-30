import random
import streamlit as st
import schedule
import streamlit.components.v1 as stcomponents
import time
import json 
import requests
from datetime import datetime
from PIL import Image
from pathlib import Path
from pathlib import Path

# Configure page to use full width - must be first Streamlit command
st.set_page_config(page_title="DingBot™ Facebook Scraper", layout="wide")

# Notification tracking (same as backend)
NOTIFICATION_TRACKING_FILE = "hot_items_notifications.json"

def load_notified_items():
    """Load the set of item IDs we've already sent notifications for"""
    try:
        if Path(NOTIFICATION_TRACKING_FILE).exists():
            with open(NOTIFICATION_TRACKING_FILE, 'r') as f:
                data = json.load(f)
                # Return set of item IDs, and clean old entries (older than 7 days)
                current_time = datetime.now().timestamp()
                week_ago = current_time - (7 * 24 * 60 * 60)  # 7 days in seconds
                
                # Filter out old entries
                fresh_items = {
                    item_id: timestamp 
                    for item_id, timestamp in data.items() 
                    if timestamp > week_ago
                }
                
                return set(fresh_items.keys())
    except Exception as e:
        print(f"Error loading notification tracking file: {e}")
    
    return set()

def add_notified_items_gui(new_item_ids):
    """Add new item IDs to the notification tracking with current timestamp (GUI version)"""
    try:
        # Load existing data as dict (item_id -> timestamp)
        notified_dict = {}
        if Path(NOTIFICATION_TRACKING_FILE).exists():
            with open(NOTIFICATION_TRACKING_FILE, 'r') as f:
                notified_dict = json.load(f)
        
        # Add new items with current timestamp
        current_time = datetime.now().timestamp()
        for item_id in new_item_ids:
            notified_dict[item_id] = current_time
        
        # Save updated data
        with open(NOTIFICATION_TRACKING_FILE, 'w') as f:
            json.dump(notified_dict, f, indent=2)
        
        print(f"GUI: Added {len(new_item_ids)} items to notification tracking")
        
    except Exception as e:
        print(f"GUI: Error adding items to notification tracking: {e}")

def extract_item_id(url):
    """Extract the item ID from a Facebook Marketplace URL (same as backend)"""
    if not url:
        return None
    
    # Handle relative URLs by converting to absolute first
    if url.startswith('/'):
        url = f"https://www.facebook.com{url}"
    
    # Look for patterns like /marketplace/item/{item_id} or /marketplace/item/{item_id}/?...
    import re
    patterns = [
        r'/marketplace/item/(\d+)',  # Most common pattern
        r'marketplace.*?item.*?(\d+)',  # Backup pattern
        r'item.*?(\d+)',  # Even more generic
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, use the full URL as fallback (shouldn't happen but safe)
    return url

def countdown_timer():
  countdown_message.empty()
  duration = 3 * 60  # 3 minutes instead of 5
  while duration:
        mins, secs = divmod(duration, 60)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        countdown_message.text(f"Time until next auto scrape: {timeformat}")
        time.sleep(1)
        duration -= 1
  countdown_message.text("Scraping...")


def ding():
  unique_id = f'dingSound_{time.time()}_{random.randint(1, 1000)}'
  audio_html = f'<audio id="{unique_id}" autoplay><source src="app/static/ding.mp3"></audio>'
  stcomponents.html(audio_html)

def crawl():  # Get current values from Streamlit widgets instead of global variables
  current_city = st.session_state.get('city', city)
  current_query = st.session_state.get('query', query)
  current_max_price = st.session_state.get('max_price', max_price)
  current_max_listings = st.session_state.get('max_listings', max_listings)

  # Workaround to hide the ugly iframe that the new results alert component gets rendered in
  st.markdown(
    """
    <style>
        iframe {
            display: none;  /* Hide the iframe */
        }
    </style>
    """,
    unsafe_allow_html=True
  )
  
  if "," in current_max_price:
      current_max_price = current_max_price.replace(",", "")
  elif "$" in current_max_price:
      current_max_price = current_max_price.replace("$", "")
  else:
      pass

  # Split the query to get individual search terms
  query_list = [q.strip() for q in current_query.split(',')]
  
  # Store results per query for column display
  results_by_query = {}
  
  # Get results for each query individually
  for individual_query in query_list:
    try:
      res = requests.get(f"http://127.0.0.1:8000/crawl_facebook_marketplace?city={current_city}&sortBy=creation_time_descend&query={individual_query}&max_price={str(int(current_max_price) * 100)}&max_results_per_query={current_max_listings}")
      query_results = res.json()
      results_by_query[individual_query] = query_results
    except:
      results_by_query[individual_query] = []

  # Flatten all results for alert checking
  all_results = []
  for query_results in results_by_query.values():
    all_results.extend(query_results)  # Display the length of the results list and check for new items
  if len(all_results) > 0:
    # Track items by their link (more reliable than title for duplicates)
    latest_items = {item["link"]: item for item in all_results}
    
    # Load already notified items from persistent storage
    already_notified = load_notified_items()
    
    # Find new hot items that haven't been notified about yet
    hot_items = {link: item for link, item in latest_items.items() if item.get('item_type') == 'hot'}
    new_hot_item_ids = []
    new_hot_items_data = []
    
    for link, item in hot_items.items():
        item_id = extract_item_id(link)
        if item_id and item_id not in already_notified:
            new_hot_item_ids.append(item_id)
            new_hot_items_data.append(item)
    
    # Only trigger ding for truly new hot items
    if len(new_hot_item_ids) > 0:
      # Get the titles of new hot items for the alert
      new_hot_titles = [item["title"] for item in new_hot_items_data]
      latest_string = "\\n\\n".join(new_hot_titles)
      
      # Add to notification tracking
      add_notified_items_gui(new_hot_item_ids)
      
      alert_js=f"alert('New HOT items!!\\n\\n{latest_string}')"
      alert_html = f"<script>{alert_js}</script>"

      # stcomponents.html(alert_html) # TODO: temporarily disabled need a better alert
      ding()
      print(f"🔥 DING! Found {len(new_hot_item_ids)} new HOT items!")
  last_ran_formatted = datetime.now().time().strftime("%I:%M:%S %p")
  results_message.markdown(f"*Showing latest {current_max_listings} listings (per query) since last scrape at **{last_ran_formatted}***")
  # Clear previous results
  results_container.empty()  # Add CSS styles for results container
  
  st.markdown("""
    <style>
    .results-container {
        max-height: 800px;
        overflow-y: auto;
        border: 2px solid #f0f0f0;
        border-radius: 8px;
        padding: 10px;
    }
    </style>
  """, unsafe_allow_html=True)
  # Display results in columns by query
  with results_container.container():
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    
    # Create columns based on number of queries
    if len(query_list) == 1:
      cols = [st.container()]
    else:
      cols = st.columns(len(query_list))
    
    # Display each query's results in its own column
    for i, (individual_query, query_results) in enumerate(results_by_query.items()):
      with cols[i]:
        st.subheader(f"🔍 {individual_query}")
        st.markdown(f"*{len(query_results)} results*")
        
        if len(query_results) == 0:
          st.info("No results found for this query")
        else:
          for item in query_results:
            # Fix URL formatting - remove duplicate facebook.com prefix
            listing_url = item['link']
            if listing_url.startswith('/'):
                listing_url = f"https://www.facebook.com{listing_url}"
            elif not listing_url.startswith('http'):
                listing_url = f"https://www.facebook.com/{listing_url}"
              # Determine item type and visual indicators
            item_type = item.get('item_type', 'unknown')
            if item_type == 'hot':
                icon = "🔥"
                badge_color = "#ff4444"
                badge_text = "HOT ITEM"
                title_prefix = "🔥 "
            elif item_type == 'new':
                icon = "✨"
                badge_color = "#44ff44"
                badge_text = "NEW"
                title_prefix = "✨ "
            elif item_type == 'suggested':
                icon = "💡"
                badge_color = "#4444ff"
                badge_text = "SUGGESTED"
                title_prefix = "💡 "
            elif item_type == 'recent':
                # No special styling for recent items without "just listed" pill
                icon = ""
                badge_color = ""
                badge_text = ""
                title_prefix = ""
            else:
                icon = ""
                badge_color = "#888888"
                badge_text = ""
                title_prefix = ""
            
            # Add badge and styling
            if badge_text:
                st.markdown(f'<div style="background-color: {badge_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; display: inline-block; margin-bottom: 5px;">{badge_text}</div>', unsafe_allow_html=True)
            
            # Make title clickable and open in new tab with visual indicator
            st.markdown(f"#### {title_prefix}[{item['title']}]({listing_url})")
            
            # Make image larger for full-width layout and clickable
            img_url = item["image"]
              # Add border styling based on item type
            if item_type == 'hot':
                border_style = "border: 3px solid #ff4444; border-radius: 8px;"
            elif item_type == 'new':
                border_style = "border: 2px solid #44ff44; border-radius: 8px;"
            elif item_type == 'suggested':
                border_style = "border: 2px solid #4444ff; border-radius: 8px;"
            elif item_type == 'recent':
                # No special border for recent items without "just listed" pill
                border_style = ""
            else:
                border_style = ""
            st.markdown(f'<a href="{listing_url}" target="_blank"><img src="{img_url}" width="350" style="cursor: pointer; max-width: 100%; {border_style}"></a>', unsafe_allow_html=True)
            
            st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)  # Close results container

  countdown_timer()

# End of private functions

# Initialize session state
if 'current_latest' not in st.session_state:
    st.session_state.current_latest = []

# Create a title for the web app.
st.title("DingBot™ Facebook Scraper")
st.subheader("Brought to you by Passivebot + WordForest")

# Add a list of supported cities.
supported_cities = ["Hamilton", "Barrie", "Toronto"] # TODO: more oNTARIO cities

# Take user input for the city, query, and max price.
city = st.selectbox("City", supported_cities, 0, key='city')
query = st.text_input("Query (comma,between,multiple,queries)", "Horror VHS,Digimon", key='query')
# TODO: don't scrape until there is an input. Ensure that subsequent auto scrapes use the input
max_price = st.text_input("Max Price ($)", "1000", key='max_price')
# This value should be calibrated to your queries. Facebook sometimes is very lax about what they think
# is related to your search query.
max_listings = st.text_input("Max Latest Listings", "8", key='max_listings')

countdown_message = st.empty()

# TODO: shouldn't clear results
submit = st.button("Force Scrape Now!")

results_message = st.empty()
results_container = st.empty()

# If the button is clicked
if submit:
  countdown_message.text("Scraping...")
  crawl()

# Schedule the scraper to run every 3 minutes
schedule.every(3).minutes.do(crawl)
# Timer message
countdown_timer() # TODO: FIRST auto scrape not working?

# Run the scheduler
while True:
  schedule.run_pending()
  time.sleep(2)  # Sleep for 1 second to avoid high CPU usage