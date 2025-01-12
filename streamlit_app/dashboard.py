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
    drilling_progress_type = st.sidebar.selectbox("Select Drilling Progress Type", ["Detailed Progress", "Daily Overview"])
    unique_well_pad_names = df['well_pad_name'].unique() if 'well_pad_name' in df.columns else []
    selected_well_pad_name = st.sidebar.selectbox(
        "Select Well Pad Name",
        options=unique_well_pad_names if len(unique_well_pad_names) > 0 else ["No data available"]
    )

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

    return filtered_data, drilling_progress_type

def handle_file_upload(url):
    """Handle file uploads via Streamlit."""
    st.sidebar.header("Report Upload")
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

            st.subheader("Report Details")
            if filtered_detail:
                # Extract the first row of the filtered_detail as a dictionary
                detail = filtered_detail[0]
                detail = {key: value if value is not None else "-" for key, value in detail.items()}

                col1, col2 = st.columns(2)

                with col1:
                    # Display contractor details

                    st.markdown(f'''
                    **Contractor:** {detail.get('contractor', 'N/A')}<br>
                    **Field:** {detail.get('field', 'N/A')}<br>
                    **Latitude/Longitude:** {detail.get('latitude_longitude', 'N/A')}
                    ''', unsafe_allow_html=True)
                    st.text('')

                    # Display supervisor details
                    st.markdown(f'''
                    **Day/Night Drilling Supervisor:** {detail.get('day_night_drilling_supv', 'N/A')}<br>
                    **Drilling Superintendent:** {detail.get('drilling_superintendent', 'N/A')}<br>
                    **Rig Superintendent:** {detail.get('rig_superintendent', 'N/A')}<br>
                    **Drilling Engineer:** {detail.get('drilling_engineer', 'N/A')}<br>
                    **HSE Supervisor:** {detail.get('hse_supervisor', 'N/A')}
                    ''', unsafe_allow_html=True)

                with col2:
                    # Display financial details
                    st.markdown(f'''
                    **AFE Number AFE Cost:** {detail.get('afe_number_afe_cost', 'N/A')}<br>
                    **Daily Cost:** {detail.get('daily_cost', 'N/A')}<br>
                    **Percent AFE Cumulative Cost:** {detail.get('percent_afe_cumulative_cost', 'N/A')}<br>
                    **Daily Mud Cost:** {detail.get('daily_mud_cost', 'N/A')}<br>
                    **Cumulative Mud Cost:** {detail.get('cumulative_mud_cost', 'N/A')}
                    ''', unsafe_allow_html=True)

                # Display summary details
                st.text('')
                st.markdown(f"**24 Hours Summary:** {detail.get('hours_24_summary', 'N/A')}")

            else:
                st.info("No details available for the selected date.")

            st.subheader("Time Breakdown")
            if filtered_time:
                filtered_time = pd.DataFrame(filtered_time)
                
                column_mapping = {
                    "start": "Start",
                    "end": "End",
                    "elapsed": "Elapsed",
                    "depth": "Depth",
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


def visualize_by_drilling_progress_type(df, drilling_progress_type):
    """Generate visualizations for Daily and Weekly time frames."""
    if df.empty:
        st.warning("No data available for visualization.")
        return

    df = preprocess_data(df)  # Ensure data is preprocessed

    if drilling_progress_type == 'Detailed Progress':
        # Daily visualization: line chart with start_time as x-axis
        x_axis = df['start_time']

        # Prepare hover text for markers
        text = df.apply(
            lambda row: (
                f"Depth: {int(row['depth']) if 'depth' in df.columns and not pd.isna(row['depth']) else ''}<br>"
                f"Time: {row['start_time'].strftime('%H:%M')}<br>"
                f"Date: {row['start_time'].strftime('%b %d, %Y')}<br>"
                f"Description: {row['description'] if 'description' in row else ''}"
            ),
            axis=1
        )

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=df['depth'] if 'depth' in df.columns else [],
            mode='lines+markers',
            name='Daily Depth',
            text=text,
            hoverinfo='text',
            line=dict(color='#c35817'),  
            marker=dict(color='#c35817')
        ))
        fig.update_layout(
            title="Drilling Activity (Hourly View)",
            xaxis_title="Date",
            yaxis_title="Depth (m)",
            legend_title="Legend",
            xaxis=dict(
                showgrid=True, 
                #gridcolor='gray',
                tickmode='linear',
                dtick=86400000.0, 
                tickformat="%b %d, %Y",
                tickfont=dict(color="black"),
                titlefont=dict(color="black")
            ),
            yaxis=dict(
                showgrid=True,
                tickfont=dict(color="black"),
                titlefont=dict(color="black"),
                range=[max(df['depth']) + 100, 0] if 'depth' in df.columns and len(df['depth']) > 0 else [1, 0]  # Reverse range
            ),
            height=515        
        )
        st.plotly_chart(fig)

    elif drilling_progress_type == 'Daily Overview':
        # Weekly visualization: bar chart with max depth per day
        if 'date' in df.columns and 'depth' in df.columns:
            weekly_data = (
                df.groupby(df['date'].dt.date)['depth']
                .agg(lambda x: (x.iloc[-1] - x.iloc[0]) if len(x) > 1 else 0)  # Calculate depth difference, handle NaN gracefully
                .reset_index()
                .rename(columns={'depth': 'depth_difference'})
            )
            weekly_data['depth_difference'] = weekly_data['depth_difference'].fillna(0)
            weekly_data['label'] = weekly_data['depth_difference'].apply(
                lambda x: "No difference" if x == 0 else int(x)
            )

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=weekly_data['date'],
                y=weekly_data['depth_difference'],
                name='Depth Difference',
                text=weekly_data['label'],  
                textposition='outside',
                marker=dict(color='#c35817')
            ))
            fig.update_layout(
                title="Daily Operational Insights",
                xaxis_title="Date",
                yaxis_title="Depth Difference (m)",
                legend_title="Legend",
                xaxis=dict(
                    dtick=86400000.0,
                    tickformat="%b %d, %Y",
                    tickfont=dict(color="black"),
                    titlefont=dict(color="black")
                ),
                yaxis=dict(
                    tickfont=dict(color="black"),
                    titlefont=dict(color="black")
                    ),
                height=515
            )
            st.plotly_chart(fig)
        else:
            st.warning("Required columns ('date' and 'depth') are missing for weekly visualization.")


def app():
    st.markdown("""
        <style>
            /* Sidebar container background */
            [data-testid=stSidebar] {
                background-color: #ffa500;
            }

            /* Simplified widget styles */
            [data-baseweb="input"],
            [data-baseweb="base-input"],
            [data-testid=stFileUploaderDropzone][tabindex="0"],
            [data-testid="stSelectboxVirtualDropdown"],
            [class="st-an st-ao st-ap st-aq st-ak st-ar st-am st-as st-at st-au st-av st-aw st-ax st-ay st-az st-b0 st-b1 st-b2 st-b3 st-b4 st-b5 st-b6 st-b7 st-b8 st-b9 st-ba st-bb st-bc"] {
                background-color: #ffc594;
                border: 2px solid #ffc594;
                border-radius: 5px; /* Consistent rounded corners */
            }
            [role="option"]:hover {
                background-color: #ffcc00;
            }
                
            [aria-selected="true"]{
                background-color: #ffcc00
            }
            /* Change filter dropdown background when selected */
            [data-baseweb="select"] > div {
                background-color: #ffc594; /* Light orange background for dropdown */
            }
                
            /* Change filter background on focus/click */
            [data-baseweb="input"]:focus,
            [data-baseweb="base-input"]:focus,
            [data-baseweb="select"]:focus,
            [data-testid=stFileUploaderDropzone][tabindex="0"]:focus,
            [class="st-an st-ao st-ap st-aq st-ak st-ar st-am st-as st-at st-au st-av st-aw st-ax st-ay st-az st-b0 st-b1 st-b2 st-b3 st-b4 st-b5 st-b6 st-b7 st-b8 st-b9 st-ba st-bb st-bc"]:focus{
                background-color: #ffcc99; /* Light orange background when focused */
                outline: none; /* Remove default outline */
                border: 2px solid #ffa500; /* Highlight border color */
            }
            
            /* Button styles */
            [data-testid=stSidebar] button {
                background-color: #ffcc00; /* Yellow background */
                border: 1px solid #ffa500; /* Border color */
                border-radius: 5px; /* Rounded corners */
            }
        </style>
    """, unsafe_allow_html=True)
    
    """Main app function to render the dashboard."""
    URL_UPLOAD = f"{API_URL}/upload"
    URL_TIMEBREAKDOWN = f"{API_URL}/time_breakdown"
    URL_DETAIL = f"{API_URL}/detail"

    # Fetch and preprocess data
    df = fetch_data(URL_TIMEBREAKDOWN)

    logo = "/Users/macbook/Documents/Mahasiswa/Proyek Akhir/final_project/data/1630641987061.jpeg"
    st.logo(logo, size="large", icon_image=logo)

    # Apply filters
    filtered_data, drilling_progress_type = apply_filters(df)

    # Handle file upload
    handle_file_upload(URL_UPLOAD)

    # Dashboard Title
    st.title("Drilling Operations Dashboard")

    # Render Visualization
    visualize_by_drilling_progress_type(filtered_data, drilling_progress_type)

    detail, time = fetch_detail_data(URL_DETAIL)

    visualize_detail_report(detail, time, filtered_data)
