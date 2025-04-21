import json
import random
import datetime
import os
import pandas as pd
import hashlib

# Configuration
NUM_EMPLOYEES = 50
OUTPUT_FILE_JSON = "data/employee_database.json"
OUTPUT_FILE_CSV = "data/employee_database.csv"
CREDENTIALS_FILE = "data/login_credentials.json"

# Sample data for generation
first_names = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa"
]

last_names = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee",
    "Walker", "Hall", "Allen", "Young", "Hernandez", "King", "Wright", "Lopez",
    "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter",
    "Mitchell", "Perez", "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans"
]

# Valley Water specific departments and positions
departments = [
    "Engineering", "Water Supply", "Communications", "Human Resources", 
    "Information Technology", "Legal", "Finance", "Environmental Services",
    "Watershed Operations", "Dam Safety", "Community Projects", "Administration"
]

positions = {
    "Engineering": ["Water Resources Engineer", "Civil Engineer", "Senior Engineer", "Engineering Manager", "Engineering Technician", "Project Manager"],
    "Water Supply": ["Water Supply Specialist", "Operations Manager", "System Operator", "Field Technician", "Water Quality Specialist"],
    "Communications": ["Communications Specialist", "Outreach Coordinator", "Media Relations Manager", "Public Affairs Representative"],
    "Human Resources": ["HR Specialist", "HR Manager", "Benefits Coordinator", "Talent Acquisition Specialist", "Employee Relations Manager"],
    "Information Technology": ["IT Specialist", "System Administrator", "Network Engineer", "IT Manager", "Database Administrator", "Security Specialist"],
    "Legal": ["Legal Counsel", "Paralegal", "Compliance Officer", "Contract Specialist", "Legal Assistant"],
    "Finance": ["Financial Analyst", "Accountant", "Budget Manager", "Payroll Specialist", "Procurement Officer"],
    "Environmental Services": ["Environmental Scientist", "Conservation Specialist", "Biologist", "Resource Planner"],
    "Watershed Operations": ["Watershed Manager", "Field Supervisor", "Maintenance Worker", "Flood Control Specialist"],
    "Dam Safety": ["Dam Safety Engineer", "Safety Inspector", "Risk Assessment Specialist", "Structural Engineer"],
    "Community Projects": ["Project Coordinator", "Community Liaison", "Grant Manager", "Planning Specialist"],
    "Administration": ["Administrative Assistant", "Office Manager", "Executive Assistant", "Records Specialist", "Board Liaison"]
}

managers = {dept: [] for dept in departments}  # Will be populated with employees who can be managers

health_plans = ["Basic Health Plan", "Standard Health Plan", "Premium Health Plan"]
dental_plans = ["Basic Dental", "Premium Dental"]
vision_plans = ["Basic Vision", "Premium Vision"]
retirement_contribution_rates = [3, 4, 5, 6, 7, 8, 9, 10]

def generate_employee_id():
    """Generate a unique employee ID in the format EMP12345"""
    return f"EMP{random.randint(10000, 99999)}"

def generate_hire_date():
    """Generate a random hire date within the last 15 years"""
    days_ago = random.randint(0, 365 * 15)  # Up to 15 years ago
    hire_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return hire_date.strftime("%Y-%m-%d")

def generate_next_review_date(hire_date):
    """Generate next review date based on hire date"""
    hire_date_obj = datetime.datetime.strptime(hire_date, "%Y-%m-%d")
    # Reviews happen on the anniversary of hire date, next upcoming one
    next_review_year = datetime.datetime.now().year
    next_review_date = datetime.datetime(next_review_year, hire_date_obj.month, hire_date_obj.day)
    
    # If the review date has passed this year, schedule for next year
    if next_review_date < datetime.datetime.now():
        next_review_date = datetime.datetime(next_review_year + 1, hire_date_obj.month, hire_date_obj.day)
    
    return next_review_date.strftime("%Y-%m-%d")

def generate_pto_balance():
    """Generate a random PTO balance between 0 and 25 days"""
    return round(random.uniform(0, 25), 1)

def generate_benefits():
    """Generate a list of enrolled benefits"""
    benefits = []
    
    # Health plan - everyone has one
    benefits.append(random.choice(health_plans))
    
    # Dental plan - 80% chance
    if random.random() < 0.8:
        benefits.append(random.choice(dental_plans))
    
    # Vision plan - 70% chance
    if random.random() < 0.7:
        benefits.append(random.choice(vision_plans))
    
    # 401(k) - 90% chance
    if random.random() < 0.9:
        contribution_rate = random.choice(retirement_contribution_rates)
        benefits.append(f"401(k) - {contribution_rate}%")
    
    return benefits

def generate_employees():
    """Generate a list of synthetic employees"""
    employees = {}
    employee_ids = set()
    
    # First pass - create all employees
    for i in range(NUM_EMPLOYEES):
        # Generate a unique employee ID
        while True:
            employee_id = generate_employee_id()
            if employee_id not in employee_ids:
                employee_ids.add(employee_id)
                break
                
        department = random.choice(departments)
        position = random.choice(positions[department])
        
        hire_date = generate_hire_date()
        
        # Generate full name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        employee = {
            "id": employee_id,
            "name": full_name,
            "position": position,
            "department": department,
            "manager": None,  # Will be assigned in the second pass
            "hire_date": hire_date,
            "pto_balance": generate_pto_balance(),
            "next_review_date": generate_next_review_date(hire_date),
            "enrolled_benefits": generate_benefits()
        }
        
        employees[employee_id] = employee
        
        # Add this employee as a potential manager for their department
        if "Manager" in position or "Director" in position or "Lead" in position or "Supervisor" in position:
            managers[department].append(employee_id)
    
    # Second pass - assign managers
    for employee_id, employee in employees.items():
        dept = employee["department"]
        potential_managers = [m for m in managers[dept] if m != employee_id]
        
        # If there are no managers in this department, leave as None
        # Otherwise, assign a random manager from the same department
        if potential_managers:
            employee["manager"] = employees[random.choice(potential_managers)]["name"]
    
    # Add test user
    employees["test"] = {
        "id": "test",
        "name": "Test User",
        "position": "System Administrator",
        "department": "Information Technology",
        "manager": None,
        "hire_date": "2020-01-01",
        "pto_balance": 15.0,
        "next_review_date": "2025-01-01",
        "enrolled_benefits": ["Premium Health Plan", "Premium Dental", "Premium Vision", "401(k) - 10%"]
    }
    
    return employees

def create_login_credentials(employees):
    """Create login credentials for all employees"""
    credentials = {}
    
    for emp_id, employee in employees.items():
        # Create a simple password (last name + last 5 chars of ID)
        if emp_id == "test":
            password = "test"  # Special case for test user
        else:
            last_name = employee["name"].split()[-1]
            password = f"{last_name.lower()}{emp_id[-5:]}"
        
        # Check if this is an administrative position
        is_admin = (
            "Manager" in employee["position"] or 
            "Director" in employee["position"] or 
            "Administrator" in employee["position"] or 
            employee["department"] == "Human Resources" or
            emp_id == "test"  # Test user is always admin
        )
        
        # Hash the password (in a real system you'd use a better algorithm)
        # For demo purposes, we'll use a simple hash
        hashed_pw = hashlib.md5(password.encode()).hexdigest()
        
        credentials[emp_id] = {
            "password_hash": hashed_pw,
            "password_plain": password,  # In a real system, you wouldn't store this!
            "is_admin": is_admin
        }
    
    return credentials

def save_employees(employees, credentials):
    """Save the employee database as JSON and CSV"""
    # Create the data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Save employees as JSON
    with open(OUTPUT_FILE_JSON, 'w') as f:
        json.dump(employees, f, indent=2)
    
    # Save as CSV
    df = pd.DataFrame([
        {
            "employee_id": emp["id"],
            "name": emp["name"],
            "position": emp["position"],
            "department": emp["department"],
            "manager": emp["manager"] if emp["manager"] else "None",
            "hire_date": emp["hire_date"],
            "pto_balance": emp["pto_balance"],
            "next_review_date": emp["next_review_date"],
            "enrolled_benefits": ", ".join(emp["enrolled_benefits"])
        }
        for emp in employees.values()
    ])
    
    df.to_csv(OUTPUT_FILE_CSV, index=False)
    
    # Save credentials
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    return OUTPUT_FILE_JSON, OUTPUT_FILE_CSV, CREDENTIALS_FILE

def main():
    print(f"Generating synthetic employee database with {NUM_EMPLOYEES} employees...")
    employees = generate_employees()
    credentials = create_login_credentials(employees)
    json_file, csv_file, cred_file = save_employees(employees, credentials)
    
    print(f"Employee database saved to {json_file} and {csv_file}")
    print(f"Login credentials saved to {cred_file}")
    
    # Print sample of the data
    print("\nSample employee data:")
    sample_id = list(employees.keys())[0]
    for key, value in employees[sample_id].items():
        print(f"{key}: {value}")
    
    # Print sample credentials
    print("\nSample login credentials (for testing only):")
    print(f"ID: {sample_id}, Password: {credentials[sample_id]['password_plain']}, Admin: {credentials[sample_id]['is_admin']}")
    print(f"Test user: ID: test, Password: test, Admin: {credentials['test']['is_admin']}")

if __name__ == "__main__":
    main()