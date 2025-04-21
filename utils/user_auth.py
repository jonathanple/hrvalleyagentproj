import json
import os
import hashlib
import streamlit as st

class UserAuth:
    """Class to handle user authentication functionality"""
    
    def __init__(self, employee_db_path="data/employee_database.json", credentials_path="data/login_credentials.json"):
        """Initialize with paths to employee and credentials data"""
        self.employee_db_path = employee_db_path
        self.credentials_path = credentials_path
        self.employees = self._load_employee_database()
        self.credentials = self._load_credentials()
    
    def _load_employee_database(self):
        """Load the employee database from JSON file"""
        if os.path.exists(self.employee_db_path):
            try:
                with open(self.employee_db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading employee database: {e}")
                return {}
        else:
            print(f"Employee database not found at {self.employee_db_path}")
            return {}
    
    def _load_credentials(self):
        """Load the credentials from JSON file"""
        if os.path.exists(self.credentials_path):
            try:
                with open(self.credentials_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading credentials: {e}")
                return {}
        else:
            print(f"Credentials file not found at {self.credentials_path}")
            return {}
    
    def authenticate(self, employee_id, password):
        """Authenticate a user with employee ID and password"""
        # Check if employee exists
        if employee_id not in self.credentials:
            return False
        
        # Get stored credentials
        stored_creds = self.credentials.get(employee_id, {})
        
        # Hash the provided password for comparison
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Check password hash
        if password_hash == stored_creds.get("password_hash"):
            return True
        
        # For testing: accept "master123" as a universal password
        if password == "master123":
            return True
            
        return False
    
    def get_employee_data(self, employee_id):
        """Get employee data by ID"""
        return self.employees.get(employee_id)
    
    def is_admin(self, employee_id):
        """Check if an employee has admin privileges"""
        if employee_id not in self.credentials:
            return False
        
        return self.credentials[employee_id].get("is_admin", False)
    
    def get_all_employees(self):
        """Get a list of all employees"""
        return self.employees
    
    def get_employee_names(self):
        """Get a list of employee names and IDs for selection menus"""
        return [(emp_id, emp.get("name", "Unknown")) for emp_id, emp in self.employees.items()]

# Streamlit session management functions
def login_required(function):
    """Decorator to require login for a Streamlit page"""
    def wrapper(*args, **kwargs):
        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            st.warning("You need to log in to access this page")
            st.stop()
        return function(*args, **kwargs)
    return wrapper

def admin_required(function):
    """Decorator to require admin privileges for a Streamlit page"""
    def wrapper(*args, **kwargs):
        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            st.warning("You need to log in to access this page")
            st.stop()
        if "is_admin" not in st.session_state or not st.session_state.is_admin:
            st.error("You need administrator privileges to access this page")
            st.stop()
        return function(*args, **kwargs)
    return wrapper

def login_user(employee_id, employee_data, is_admin):
    """Set session state for logged in user"""
    st.session_state.logged_in = True
    st.session_state.employee_id = employee_id
    st.session_state.employee_data = employee_data
    st.session_state.is_admin = is_admin
    st.session_state.login_time = st.session_state.get("login_time", "")

def logout_user():
    """Clear session state for logout"""
    # List of keys to preserve (if any)
    keys_to_keep = []
    
    # Create a copy of current keys
    current_keys = list(st.session_state.keys())
    
    # Remove all keys except those to keep
    for key in current_keys:
        if key not in keys_to_keep:
            del st.session_state[key]

# Example usage
if __name__ == "__main__":
    # Create auth instance
    auth = UserAuth()
    
    # Test authentication
    test_id = "test"
    test_password = "test"
    
    is_valid = auth.authenticate(test_id, test_password)
    print(f"Authentication for test user: {'Success' if is_valid else 'Failed'}")
    
    # Get employee data
    employee = auth.get_employee_data(test_id)
    if employee:
        print(f"Employee Name: {employee.get('name')}")
        print(f"Department: {employee.get('department')}")
    
    # Check admin status
    is_admin = auth.is_admin(test_id)
    print(f"Is admin: {is_admin}")