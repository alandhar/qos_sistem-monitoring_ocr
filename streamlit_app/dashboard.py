import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

api_url_upload_data = "http://localhost:5000/upload" 
file_path = '/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/processed_data/time_breakdown.csv'
data_timebreakdown = pd.read_csv(file_path)

data_timebreakdown['date'] = pd.to_datetime(data_timebreakdown['date'])
start_date = data_timebreakdown['date'].min()
end_date = data_timebreakdown['date'].max()


# Sidebar: File Upload and Filters
st.sidebar.header("Filters")

selected_start_date = st.sidebar.date_input("Start Date", start_date)
selected_end_date = st.sidebar.date_input("End Date", end_date)
time_frame = st.sidebar.selectbox("Select Time Frame", ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])

additional_filter = st.sidebar.text_input("Additional Filter", placeholder="Optional")
uploaded_file = st.sidebar.file_uploader("Upload Drilling Report", type="pdf")

if uploaded_file is not None :
    st.sidebar.write("File uploaded:", uploaded_file.name)
    files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
    try:
        response = requests.post(url=api_url_upload_data, files=files)

        if response.status_code == 201:
            st.sidebar.success("Data uploaded successfully!")
        else:
            error_message = response.json().get('message', 'Unknown error')
            st.sidebar.error(f"{error_message}")
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"{str(e)}")

# Title of the Streamlit app
st.title("Drilling Monitoring Dashboard")
# Main: Monitoring Data Visualization
st.header("Monitoring Data Visualization")
