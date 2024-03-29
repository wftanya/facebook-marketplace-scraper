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
  res = requests.get(f"http://127.0.0.1:8000/crawl_facebook_marketplace?city={city}&sortBy=creation_time_descend&query={query}&max_price={str(int(max_price) * 100)}&max_results_per_query={max_listings}")

  # Convert the response from json into a Python list.
  results = res.json()

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
query = st.text_input("Query (comma,between,multiple,queries)", "VHS,Digimon,playstation 1")
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



# TODO: crash randomly at night. on sleep? could it be due to facebook showing the "login to see more " modal?
# 2024-01-17 23:49:25.548 Uncaught app exception
# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/requests/models.py", line 971, in json
#     return complexjson.loads(self.text, **kwargs)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/__init__.py", line 346, in loads
#     return _default_decoder.decode(s)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/decoder.py", line 337, in decode
#     obj, end = self.raw_decode(s, idx=_w(s, 0).end())
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/decoder.py", line 355, in raw_decode
#     raise JSONDecodeError("Expecting value", s, err.value) from None
# json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

# During handling of the above exception, another exception occurred:

# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 534, in _run_script
#     exec(code, module.__dict__)
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 89, in <module>
#     while True:
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 822, in run_pending
#     default_scheduler.run_pending()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 100, in run_pending
#     self._run_job(job)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 172, in _run_job
#     ret = job.run()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 693, in run
#     ret = self.job_func()
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 41, in crawl
#     results = res.json()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/requests/models.py", line 975, in json
#     raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
# requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
# 2024-01-17 23:49:25.551 Uncaught app exception
# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/requests/models.py", line 971, in json
#     return complexjson.loads(self.text, **kwargs)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/__init__.py", line 346, in loads
#     return _default_decoder.decode(s)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/decoder.py", line 337, in decode
#     obj, end = self.raw_decode(s, idx=_w(s, 0).end())
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/json/decoder.py", line 355, in raw_decode
#     raise JSONDecodeError("Expecting value", s, err.value) from None
# json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

# During handling of the above exception, another exception occurred:

# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 534, in _run_script
#     exec(code, module.__dict__)
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 89, in <module>
#     while True:
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 822, in run_pending
#     default_scheduler.run_pending()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 100, in run_pending
#     self._run_job(job)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 172, in _run_job
#     ret = job.run()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 693, in run
#     ret = self.job_func()
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 41, in crawl
#     results = res.json()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/requests/models.py", line 975, in json
#     raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
# requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
# DVD/VHS Player $15 (o.b.o)
# []
# Digimon Omegamon Pure X-Body Model Kit Built
# []
# |^\  Stopping...
# ^\  Stopping...
# Exception ignored in: <module 'threading' from '/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/threading.py'>
# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/threading.py", line 1448, in _shutdown
#     lock.acquire()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/web/bootstrap.py", line 69, in signal_handler
#     server.stop()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/web/server/server.py", line 397, in stop
#     self._runtime.stop()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/runtime/runtime.py", line 308, in stop
#     async_objs.eventloop.call_soon_threadsafe(stop_on_eventloop)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/asyncio/base_events.py", line 791, in call_soon_threadsafe
#     self._check_closed()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/asyncio/base_events.py", line 510, in _check_closed
#     raise RuntimeError('Event loop is closed')
# RuntimeError: Event loop is closed
# ➜  facebook-marketplace-scraper git:(main) ✗ streamlit run gui.py


# TODO: another crash
# []
# 2024-01-23 21:40:27.516 Uncaught app exception
# Traceback (most recent call last):
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 534, in _run_script
#     exec(code, module.__dict__)
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 130, in <module>
#     schedule.run_pending()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 822, in run_pending
#     default_scheduler.run_pending()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 100, in run_pending
#     self._run_job(job)
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 172, in _run_job
#     ret = job.run()
#   File "/Users/hifyre/.pyenv/versions/3.9.6/lib/python3.9/site-packages/schedule/__init__.py", line 693, in run
#     ret = self.job_func()
#   File "/Users/hifyre/Codes/facebook-marketplace-scraper/gui.py", line 91, in crawl
# AttributeError: '_GeneratorContextManager' object has no attribute 'empty'