import streamlit as st
import requests, html
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:5000"

def fetch_data(url):
    """Fetch data from the API endpoint."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')  # Convert 'date' column
                return df
            else:
                st.warning("No data available.")
                return pd.DataFrame()
        else:
            st.error("Failed to retrieve data from the database.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

def fetch_detail_data(url):
    """
    Fetch detailed data and time breakdown data from the /detail endpoint.

    Parameters:
    - url: The URL of the /detail endpoint.

    Returns:
    - A tuple containing:
        - detail: A list of dictionaries with detailed report data.
        - time: A list of dictionaries with time breakdown data.
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            detail_time_data = response.json()
            detail = detail_time_data.get("detail", [])
            time = detail_time_data.get("time", [])
            return detail, time
        else:
            st.error("Failed to fetch detail and time data.")
            return [], []
    except Exception as e:
        st.error(f"Error fetching detail and time data: {str(e)}")
        return [], []

def preprocess_data(df):
    """Preprocess data for visualization."""
    if df.empty:
        return pd.DataFrame()

    min_date = df['date'].min()
    max_date = df['date'].max()
    complete_dates = pd.date_range(start=min_date, end=max_date)

    missing_dates = complete_dates.difference(df['date'])
    missing_data = pd.DataFrame({'date': missing_dates})

    for col in df.columns:
        if col == 'start':
            missing_data[col] = 0
        elif col == 'end':
            missing_data[col] = 0
        elif col != 'date':
            missing_data[col] = None

    df = pd.concat([df, missing_data], ignore_index=True)
    df['start'] = pd.to_numeric(df.get('start', 0), errors='coerce').fillna(0)
    df['end'] = pd.to_numeric(df.get('end', 0), errors='coerce').fillna(0)

    df['start_time'] = df['date'] + pd.to_timedelta(df['start'], unit='h')
    df['end_time'] = df['date'] + pd.to_timedelta(df['end'], unit='h')

    df = df.sort_values(by='start_time').reset_index(drop=True)
    return df

def apply_filters(df):
    """Apply sidebar filters to the data."""
    st.sidebar.header("Filters")
    unique_well_pad_names = df['well_pad_name'].unique() if 'well_pad_name' in df.columns else []
    selected_well_pad_name = st.sidebar.selectbox(
        "Select Well Pad Name:",
        options=unique_well_pad_names if len(unique_well_pad_names) > 0 else ["No data available"]
    )
    time_frame = st.sidebar.selectbox("Select Time Frame", ['Daily', 'Weekly'])

    if not df.empty and selected_well_pad_name != "No data available":
        filtered_data = df[df['well_pad_name'] == selected_well_pad_name]
    else:
        filtered_data = pd.DataFrame()

    if not filtered_data.empty:
        start_date, end_date = filtered_data['date'].min(), filtered_data['date'].max()
        date_range = st.sidebar.date_input("Select Date Range",
                                           value=(start_date.date(), end_date.date()),
                                           min_value=start_date,
                                           max_value=end_date)
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_data = filtered_data[
                (filtered_data['date'] >= pd.to_datetime(start_date)) &
                (filtered_data['date'] <= pd.to_datetime(end_date))
            ]

    return filtered_data, time_frame

def handle_file_upload(url):
    """Handle file uploads via Streamlit."""
    uploaded_files = st.sidebar.file_uploader("Upload Drilling Reports (PDFs)", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        try:
            files = [('files', (file.name, file, 'application/pdf')) for file in uploaded_files]
            response = requests.post(url, files=files)
            if response.status_code == 207:  # Multi-Status response
                results = response.json().get("results", [])
                for result in results:
                    message = result.get("message", "No message provided")
                    if "successfully" in message.lower():
                        st.sidebar.success(f"{message}")
                    else:
                        st.sidebar.error(f"{message}")
            else:
                st.sidebar.error(response.json().get("message", "Failed to upload files"))
        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Upload error: {str(e)}")

def visualize_detail_report(detail, time, filtered_data):
    """
    Display details using an expander and filter based on a date selection.
    
    Parameters:
    - detail: List of dictionaries containing detailed report data.
    - time: List of dictionaries containing time breakdown data.
    - filtered_data: DataFrame containing the filtered data to extract unique dates.
    """
    if filtered_data.empty:
        st.warning("No data available to display details.")
        return

    # Extract unique dates from filtered_data
    formatted_dates = filtered_data['date'].dt.strftime("%d %B %Y").unique()
    date_mapping = dict(zip(formatted_dates, filtered_data['date'].dt.date.unique()))  # Map formatted to raw dates

    # Create an expander for date selection and display details
    with st.expander("View Details"):
        # Create the selectbox with formatted dates
        selected_formatted_date = st.selectbox("Select Date", options=formatted_dates)

        # Map back to the raw date
        selected_date = date_mapping[selected_formatted_date]

        if selected_date:
            # Match the id of the selected date with details and time
            filtered_ids = filtered_data[filtered_data['date'].dt.date == selected_date]['profile_id'].unique()

            # Filter detail and time data based on matched IDs
            filtered_detail = [item for item in detail if item['id'] in filtered_ids]
            filtered_time = [item for item in time if item['profile_id'] in filtered_ids]

            st.subheader("Detailed Report")
            if filtered_detail:
                st.table(pd.DataFrame(filtered_detail))
            else:
                st.info("No details available for the selected date.")

            st.subheader("Time Breakdown")
            if filtered_time:
                filtered_time = pd.DataFrame(filtered_time)
                
                column_mapping = {
                    "start": "Start",
                    "end": "End",
                    "elapsed": "Elapsed",
                    "pt_npt": "PT/NPT",
                    "code": "Code",
                    "description": "Description",
                    "operation": "Operations"
                }

                filtered_time.rename(columns=column_mapping, inplace=True)

                # Reorder columns based on the column_rename_mapping
                desired_column_order = list(column_mapping.values())  # Get the new column names in order
                filtered_time = filtered_time[desired_column_order]

                st.dataframe(
                    filtered_time,
                    use_container_width=True,
                    #height=700,
                    hide_index=True,
                    # key="data",
                    on_select="rerun",
                    selection_mode=["multi-column"],
                )

            else:
                st.info("No time breakdown available for the selected date.")


def visualize_by_time_frame(df, time_frame):
    """Generate visualizations for Daily and Weekly time frames."""
    if df.empty:
        st.warning("No data available for visualization.")
        return

    df = preprocess_data(df)  # Ensure data is preprocessed

    if time_frame == 'Daily':
        # Daily visualization: line chart with start_time as x-axis
        x_axis = df['start_time']
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=df['depth'] if 'depth' in df.columns else [],
            mode='lines+markers',
            name='Daily Depth'
        ))
        fig.update_layout(
            title="Daily Drilling Depth",
            xaxis_title="Time",
            yaxis_title="Depth",
            legend_title="Legend"
        )
        st.plotly_chart(fig)

    elif time_frame == 'Weekly':
        # Weekly visualization: bar chart with max depth per day
        if 'date' in df.columns and 'depth' in df.columns:
            weekly_data = (
                df.groupby(df['date'].dt.date)['depth']
                .max()
                .reset_index()
                .rename(columns={'depth': 'max_depth'})
            )

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=weekly_data['date'],
                y=weekly_data['max_depth'],
                name='Max Depth'
            ))
            fig.update_layout(
                title="Weekly Max Drilling Depth",
                xaxis_title="Date",
                yaxis_title="Max Depth",
                legend_title="Legend"
            )
            st.plotly_chart(fig)
        else:
            st.warning("Required columns ('date' and 'depth') are missing for weekly visualization.")


def app():
    """Main app function to render the dashboard."""
    URL_UPLOAD = f"{API_URL}/upload"
    URL_TIMEBREAKDOWN = f"{API_URL}/time_breakdown"
    URL_DETAIL = f"{API_URL}/detail"

    # Fetch and preprocess data
    df = fetch_data(URL_TIMEBREAKDOWN)

    logo = "/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/1630641987061.jpeg"
    st.logo(logo, size="large", icon_image=logo)

    # Apply filters
    filtered_data, time_frame = apply_filters(df)

    # Handle file upload
    handle_file_upload(URL_UPLOAD)

    # Dashboard Title
    st.title("PT. GEO DIPA ENERGI (Persero)")
    st.header("Drilling Operations Dashboard")

    # Render Visualization
    visualize_by_time_frame(filtered_data, time_frame)

    detail, time = fetch_detail_data(URL_DETAIL)

    visualize_detail_report(detail, time, filtered_data)
    
    if not filtered_data.empty:
        # Rename columns
        column_rename_mapping = {
            "date": "Drilling Date",
            "depth": "Drilling Depth",
            "end": "End",
            "elapsed": "Elapsed Time",
            # Add any additional column renaming as needed
        }
        filtered_data.rename(columns=column_rename_mapping, inplace=True)

        # Reorder columns based on the column_rename_mapping
        desired_column_order = list(column_rename_mapping.values())  # Get the new column names in order
        filtered_data = filtered_data[desired_column_order]

        # Display the dataframe without sorting functionality
        st.dataframe(
            filtered_data.style.format({"Drilling Date": lambda x: x}),  # Format date column
            use_container_width=True,
            height=700,
            hide_index=True,
            column_config={
                "Drilling Date": st.column_config.DateColumn(format="DD MMMM YYYY")
            },
            # key="data",
            on_select="rerun",
            selection_mode=["multi-column"],
        )
    else:
        st.warning("No data available to display.")

