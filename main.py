import streamlit as st
import os
import sys

# Configure Streamlit page (keep this one)
st.set_page_config(
    page_title="Valley Water HR Assistant",
    page_icon="👩‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add the current directory to the path so Python can find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def main():
    """Main entry point for the application"""
    # Initialize directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/pdfs", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)
    
    # Check if user is logged in
    if "logged_in" in st.session_state and st.session_state.logged_in:
        # If logged in, redirect to appropriate portal
        if st.session_state.get("is_admin", False):
            st.switch_page("pages/admin_portal.py")
        else:
            st.switch_page("pages/employee_portal.py")
    else:
        # Login page content directly here
        from pages.login import main as login_main
        login_main()

if __name__ == "__main__":
    main()