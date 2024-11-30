import random
import streamlit as st
import schedule
import streamlit.components.v1 as stcomponents
import time
import json 
import requests
from datetime import datetime
from PIL import Image

def countdown_timer():
  countdown_message.empty()
  duration = 5 * 60
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

def crawl():
  global max_price
  global city
  global query

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
  
  if "," in max_price:
      max_price = max_price.replace(",", "")
  elif "$" in max_price:
      max_price = max_price.replace("$", "")
  else:
      pass

  # Convert the response from json into a Python list.
  try:
    res = requests.get(f"http://127.0.0.1:8000/crawl_facebook_marketplace?city={city}&sortBy=creation_time_descend&query={query}&max_price={str(int(max_price) * 100)}&max_results_per_query={max_listings}")
    results = res.json()
  except: # TODO: this crashes every now and then without a restart being triggered on app.py
    results = []

  # Display the length of the results list.
  if len(results) > 0:
    # Determine if there are new results and log an alert if so
    latest = [json.dumps(item["title"]) for item in results] # TODO: index on url instead of title in case of dupes
    diff = [item for item in latest if item not in st.session_state.current_latest]
    if len(diff) > 0:
      # Reset the latest list
      st.session_state.current_latest = latest
      latest_string = "\\n\\n".join(diff)
      # TODO: still getting repeat alerts. perhaps when random login prompt?
      alert_js=f"alert('New listings!!\\n\\n{latest_string}')"
      alert_html = f"<script>{alert_js}</script>"

      stcomponents.html(alert_html)
      ding()

  last_ran_formatted = datetime.now().time().strftime("%I:%M:%S %p")
  results_message.markdown(f"*Showing latest {max_listings} listings (per query) since last scrape at **{last_ran_formatted}***")

  # Clear previous results
  results_container.empty()

  # Iterate over the results list to display each item.
  # TODO: new! badge. query headings
  with results_container.container():
    for item in results:
        st.header(item["title"])
        img_url = item["image"] # TODO: make the whole row clickable link to listing
        st.image(img_url, width=200)
        st.write(f"https://www.facebook.com{item['link']}")
        st.write("----")

  countdown_timer()

# End of private functions

# Initialize session state
if 'current_latest' not in st.session_state:
    st.session_state.current_latest = []

# Create a title for the web app.
st.title("DingBot™ Facebook Scraper")
st.subheader("Brought to you by Passivebot + WordForest")

# Add a list of supported cities.
supported_cities = ["Hamilton"] # TODO: more oNTARIO cities

# Take user input for the city, query, and max price.
city = st.selectbox("City", supported_cities, 0)
query = st.text_input("Query (comma,between,multiple,queries)", "Digimon,Free VHS,Horror VHS")
max_price = st.text_input("Max Price ($)", "1000")
# This value should be calibrated to your queries. Facebook sometimes is very lax about what they think
# is related to your search query.
max_listings = st.text_input("Max Latest Listings", "8")
# TODO: auto scrape every 3, 5, 10, 30 minutes select

countdown_message = st.empty()

# TODO: shouldn't clear results
submit = st.button("Force Scrape Now!")

results_message = st.empty()
results_container = st.empty()

# If the button is clicked
if submit:
  countdown_message.text("Scraping...")
  crawl()

# Schedule the scraper to run every 5 minutes # TODO: interval to variable
schedule.every(5).minutes.do(crawl)
# Timer message
countdown_timer() # TODO: FIRST auto scrape not working?

# Run the scheduler
while True:
  schedule.run_pending()
  time.sleep(2)  # Sleep for 1 second to avoid high CPU usage