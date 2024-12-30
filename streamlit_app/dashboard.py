import streamlit as st
import requests
import pandas as pd
import plotly.express as px

api_url_upload_data = "http://localhost:5000/upload" 
file_path = '/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/processed_data/time_breakdown.csv'
df = pd.read_csv(file_path)

df['date'] = pd.to_datetime(df['date'])
df['timestamp'] = df['date'] + pd.to_timedelta(df['start'], unit='H')


st.sidebar.header("Filters")

# Select Time Frame 
time_frame = st.sidebar.selectbox("Select Time Frame", ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])
if time_frame == "Weekly":
    df['time_frame'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
elif time_frame == "Monthly":
    df['time_frame'] = df['date'].dt.to_period('M').apply(lambda r: r.start_time)
else:
    df['time_frame'] = df['date']

# Select Date by Time Frame
start_date = st.sidebar.date_input("Start Date", value=df['date'].min())
end_date = st.sidebar.date_input("End Date", value=df['date'].max())
date_range = pd.date_range(start=start_date, end=end_date, freq='D')
filtered_df = df[df['date'].isin(date_range)]

additional_filter = st.sidebar.text_input("Additional Filter", placeholder="Optional")

# Upload Report File Drilling
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


st.title("PT. GEO DIPA ENERGI (Persero)")
st.header("Drilling Operations Dashboard")

# Plot the time series chart with points
fig = px.scatter(
    filtered_df,
    x="timestamp",
    y="depth",
    title="Drilling Depth Over Time (with Points)",
    labels={"timestamp": "Timestamp", "depth": "Depth (m)"},
    range_y=[0, max(filtered_df['depth'])]  # Ensure y-axis starts at 0
)

# Add line to connect points
fig.add_scatter(
    x=filtered_df['timestamp'],
    y=filtered_df['depth'],
    mode='lines',
    name='Depth Trend'
)

st.plotly_chart(fig)