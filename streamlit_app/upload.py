import streamlit as st
import requests

API_URL = "http://localhost:5000"
URL_UPLOAD = f"{API_URL}/upload"

def app():
    st.markdown("""
        <style>
            /* Simplified widget styles */
            [data-testid=stFileUploaderDropzone][tabindex="0"]{
                background-color: #ffc594;
                border: 2px solid #ffc594;
                border-radius: 5px; /* Consistent rounded corners */
            }
            
            /* Button styles */
            [data-testid="stFileUploaderDropzone"] button {
                background-color: #ffcc00; /* Yellow background */
                border: 1px solid #ffa500; /* Border color */
                border-radius: 5px; /* Rounded corners */
            }
        </style>
    """, unsafe_allow_html=True)


    st.title("Upload Drilling Reports")

    uploaded_files = st.file_uploader("Choose files", type="pdf", accept_multiple_files=True)

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
                        st.success(f"{message}")
                    else:
                        st.error(f"{message}")
            else:
                st.error(
                    response.json().get("message", "Failed to upload files")
                )

        except requests.exceptions.RequestException as e:
            st.error(f"Upload error: {str(e)}")