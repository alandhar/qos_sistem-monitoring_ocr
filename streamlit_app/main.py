import os
import streamlit as st
import requests
from upload import app as upload_app
from dashboard import app as dashboard_app
from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv("API_URL")
URL_TIMEBREAKDOWN = f"{API_URL}/time_breakdown"

st.set_page_config(page_title="Multi-Page App", layout="wide")

logo = os.getenv("LOGO")
st.logo(logo, size="large", icon_image=logo)

# Check if there is data in the database
try:
    response = requests.get(URL_TIMEBREAKDOWN)
    if response.status_code == 200:
        data = response.json()
        has_data = bool(data)  # Check if the response contains any data
    else:
        st.error("Failed to connect to the database.")
        has_data = False
except Exception as e:
    st.error(f"Error checking database: {str(e)}")
    has_data = False

# Page Rendering
if has_data:
    dashboard_app()  # Render the dashboard if data exists
else:
    upload_app()