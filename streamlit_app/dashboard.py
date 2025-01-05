import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:5000"

# API Endpoint
URL_UPLOAD = f"{API_URL}/upload"
URL_TIMEBREAKDOWN = f"{API_URL}/time_breakdown"

# Fetch Data from API
try:
    response = requests.get(URL_TIMEBREAKDOWN)
    if response.status_code == 200:
        data = response.json()
        if data:
            df = pd.DataFrame(data)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')  # Convert date safely
            else:
                st.warning("The 'date' column is missing in the dataset.")
        else:
            st.warning("No data available from the database.")
            df = pd.DataFrame()  # Create an empty DataFrame
    else:
        st.error("Failed to retrieve data from the database.")
        df = pd.DataFrame()
except Exception as e:
    st.error(f"Error fetching data: {str(e)}")
    df = pd.DataFrame()  # Ensure app runs even on error

# Safeguard for missing columns
if not df.empty and 'well_pad_name' not in df.columns:
    df['well_pad_name'] = None  # Add column with default value if missing
if not df.empty and 'start' not in df.columns:
    df['start'] = 0  # Add start column with default value if missing
if not df.empty and 'end' not in df.columns:
    df['end'] = 0  # Add end column with default value if missing

# Preprocess Data
def preprocess_data(df):
    if df.empty:
        return pd.DataFrame()  # Return empty DataFrame if no data

    # Generate complete date range
    if 'date' in df.columns:
        min_date = df['date'].min()
        max_date = df['date'].max()
        complete_dates = pd.date_range(start=min_date, end=max_date)
        missing_dates = complete_dates.difference(df['date'])
        missing_data = pd.DataFrame({'date': missing_dates})
        for col in df.columns:
            if col != 'date':
                missing_data[col] = None  # Assign default values for missing rows
        df = pd.concat([df, missing_data], ignore_index=True)
    else:
        st.warning("Missing 'date' column in data for preprocessing.")

    # Ensure numeric columns
    df['start'] = pd.to_numeric(df.get('start', 0), errors='coerce').fillna(0)
    df['end'] = pd.to_numeric(df.get('end', 0), errors='coerce').fillna(0)

    # Calculate start_time and end_time if 'date' column exists
    if 'date' in df.columns:
        df['start_time'] = df['date'] + pd.to_timedelta(df['start'], unit='h')
        df['end_time'] = df['date'] + pd.to_timedelta(df['end'], unit='h')

    # Sort data
    if 'start_time' in df.columns:
        df = df.sort_values(by='start_time').reset_index(drop=True)
    return df

# Sidebar Filters
st.sidebar.header("Filters")
unique_well_pad_names = df['well_pad_name'].dropna().unique().tolist() if 'well_pad_name' in df.columns else []
selected_well_pad_name = st.sidebar.selectbox(
    "Select Well Pad Name:",
    options=unique_well_pad_names if len(unique_well_pad_names) > 0 else ["No data available"]
)
time_frame = st.sidebar.selectbox("Select Time Frame", ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])

if not df.empty and selected_well_pad_name != "No data available":
    filtered_data = df[df['well_pad_name'] == selected_well_pad_name]
else:
    filtered_data = pd.DataFrame()  # Empty DataFrame for invalid filters

if not filtered_data.empty and 'date' in filtered_data.columns:
    start_date, end_date = filtered_data['date'].min(), filtered_data['date'].max()
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(start_date.date(), end_date.date()),
        min_value=start_date.date(),
        max_value=end_date.date()
    )
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_data = filtered_data[
            (filtered_data['date'] >= pd.to_datetime(start_date)) &
            (filtered_data['date'] <= pd.to_datetime(end_date))
        ]

# Upload Drilling Reports
uploaded_files = st.sidebar.file_uploader("Upload Drilling Reports (PDFs)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    try:
        files = [('files', (file.name, file, 'application/pdf')) for file in uploaded_files]
        response = requests.post(URL_UPLOAD, files=files)
        if response.status_code == 207:  # Multi-Status
            results = response.json().get("results", [])
            for result in results:
                message = result.get("message", "No message")
                if "successfully" in message.lower():
                    st.sidebar.success(message)
                else:
                    st.sidebar.error(message)
        else:
            st.sidebar.error("File upload failed.")
    except Exception as e:
        st.sidebar.error(f"File upload error: {str(e)}")

# Dashboard Title
st.title("PT. GEO DIPA ENERGI (Persero)")
st.header("Drilling Operations Dashboard")

# Visualization
def visual(filter_option, df):
    if df.empty:
        st.warning("No data available for visualization.")
        return

    df = preprocess_data(df)
    if filter_option == 'Daily':
        x_axis = df['start_time']
    else:
        x_axis = df['date']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=df['depth'] if 'depth' in df.columns else [],
        mode='lines+markers' if filter_option == 'Daily' else 'lines',
        name=f'{filter_option} Visualization'
    ))

    fig.update_layout(
        title=f"Drilling Monitoring - {filter_option}",
        xaxis_title="Time",
        yaxis_title="Depth",
        legend_title="Legend"
    )

    st.plotly_chart(fig)

# Render Visualization
visual(time_frame, filtered_data)