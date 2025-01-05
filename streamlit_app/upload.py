import streamlit as st
import requests

API_URL = "http://localhost:5000"
URL_UPLOAD = f"{API_URL}/upload"

def app():
    st.title("Upload Upload Drilling Reports (PDFs)")

    uploaded_files = st.file_uploader(
    "Upload Drilling Reports (PDFs)", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        try:
            files = [
                ('files', (file.name, file, 'application/pdf')) for file in uploaded_files
            ]

            response = requests.post(url=URL_UPLOAD, files=files)

            if response.status_code == 207:  # Multi-Status response
                results = response.json().get("results", [])
                for result in results:
                    filename = result.get("filename", "Unknown File")
                    message = result.get("message", "No message provided")
                    if "successfully" in message.lower():
                        st.sidebar.success(f"{message}")
                    else:
                        st.sidebar.error(f"{message}")
            else:
                st.sidebar.error(
                    response.json().get("message", "Failed to upload files")
                )

        except requests.exceptions.RequestException as e:
            st.sidebar.error(f"Upload error: {str(e)}")