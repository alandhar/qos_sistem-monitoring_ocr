import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# API Endpoint
API_URL_UPLOAD = "http://localhost:5000/upload"

# Load Data
FILE_PATH = '/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/processed_data/time_breakdown.csv'
df = pd.read_csv(FILE_PATH)

df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Preprocess the Data
def preprocess_data(df):
    
    # Generate complete date range
    min_date = df['date'].min()
    max_date = df['date'].max()
    complete_dates = pd.date_range(start=min_date, end=max_date)

    # Identify missing dates and append
    missing_dates = complete_dates.difference(df['date'])
    missing_data = pd.DataFrame({'date': missing_dates})
    
    # Assign default values for missing data
    for col in df.columns:
        if col == 'start':
            missing_data[col] = 0  # Default start value for missing rows
        elif col == 'end':
            missing_data[col] = 0  # Default end value for missing rows
        elif col != 'date':
            missing_data[col] = None  # None for other columns

    # Combine original and missing data
    df = pd.concat([df, missing_data], ignore_index=True)

    # Ensure 'start' and 'end' columns exist and are numeric
    df['start'] = pd.to_numeric(df.get('start', 0), errors='coerce').fillna(0)
    df['end'] = pd.to_numeric(df.get('end', 0), errors='coerce').fillna(0)

    # Calculate 'start_time' and 'end_time'
    df['start_time'] = df['date'] + pd.to_timedelta(df['start'], unit='h')
    df['end_time'] = df['date'] + pd.to_timedelta(df['end'], unit='h')

    # Sort data by 'start_time'
    df = df.sort_values(by='start_time').reset_index(drop=True)
    return df

# Sidebar Filters
st.sidebar.header("Filters")
time_frame = st.sidebar.selectbox("Select Time Frame", ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])
start_date = st.sidebar.date_input("Start Date", value=df['date'].min())
end_date = st.sidebar.date_input("End Date", value=df['date'].max())
filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
# Optional Additional Filter
additional_filter = st.sidebar.text_input("Additional Filter (Optional)")

# Upload Drilling Report
uploaded_file = st.sidebar.file_uploader("Upload Drilling Report (PDF)", type="pdf")
if uploaded_file:
    try:
        files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
        response = requests.post(url=API_URL_UPLOAD, files=files)
        if response.status_code == 201:
            st.sidebar.success("File uploaded successfully!")
        else:
            st.sidebar.error(response.json().get('message', "Failed to upload file"))
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Upload error: {str(e)}")

# Dashboard Title
st.title("PT. GEO DIPA ENERGI (Persero)")
st.header("Drilling Operations Dashboard")

# Visualization
def visual(filter_option, df):
    df = preprocess_data(df)

    if filter_option == 'Daily':
        x_axis = df['start_time']
    else:
        x_axis = df['date']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=df['depth'],
        mode='lines+markers' if filter_option == 'Daily' else 'lines',
        name=f'{filter_option} Visualization',
    ))

    fig.update_layout(
        title=f"Drilling Monitoring - {filter_option}",
        xaxis_title="Time",
        yaxis_title="Depth",
        legend_title="Legend"
    )

    st.plotly_chart(fig)

# Render Visualization
visual(time_frame, filtered_df)