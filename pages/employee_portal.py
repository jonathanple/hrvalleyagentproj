import streamlit as st
import os
import time
import re
from datetime import datetime
import json
import openai
from utils.user_auth import login_required, logout_user
from utils.pdf_processor import PDFProcessor
from utils.db_manager import DBManager

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        font-size: 2rem !important;
        margin-bottom: 1rem;
        color: #0078D7;
    }

    .chat-container {
        border-radius: 10px;
        background-color: #f8f9fa;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    .chat-message {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        max-width: 80%;
    }

    .chat-message.user {
        background-color: #E3F2FD;
        margin-left: auto;
        margin-right: 0;
    }

    .chat-message.assistant {
        background-color: #F5F5F5;
        margin-right: auto;
        margin-left: 0;
    }

    .logout-btn {
        position: absolute;
        top: 1rem;
        right: 1rem;
    }

    .suggestion-btn {
        margin: 0.25rem;
    }

    .stButton button {
        border-radius: 20px;
    }

    .profile-container {
        padding: 1rem;
        border-radius: 8px;
        background-color: #f8f9fa;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    .sidebar .profile-pic {
        border-radius: 50%;
        overflow: hidden;
        margin-bottom: 1rem;
    }

    .footer {
        text-align: center;
        padding: 1rem;
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 2rem;
    }

    /* Style for resource links */
    .resource-link {
        background-color: #f0f7ff;
        border-left: 3px solid #0078D7;
        padding: 8px 12px;
        margin: 8px 0;
        border-radius: 0 4px 4px 0;
    }

    /* Style for headers in chat */
    .chat-header {
        color: #0078D7;
        margin-top: 12px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize components
pdf_processor = PDFProcessor()
db_manager = DBManager()

# Initialize OpenAI client
def get_openai_client():
    """Initialize OpenAI API client."""
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("openai_api_key", "")
    
    if not api_key:
        st.warning("OpenAI API key not found. Chatbot functionality will be limited.")
        return None
    openai.api_key = api_key
    print(f"Using API key: {api_key[:8]}...")  # Print first few characters for debugging
    return openai

# Resource links database
RESOURCE_LINKS = {
    "health insurance": "https://valleywater.org/employee/benefits/health-insurance",
    "dental insurance": "https://valleywater.org/employee/benefits/dental-insurance",
    "vision insurance": "https://valleywater.org/employee/benefits/vision-care",
    "retirement": "https://valleywater.org/employee/benefits/retirement-plans",
    "401k": "https://valleywater.org/employee/benefits/retirement-plans",
    "pension": "https://valleywater.org/employee/benefits/retirement-plans",
    # Time Off, Policies, Procedures, etc...
}

def calculate_tenure(hire_date_str):
    """Calculate employee tenure based on hire date"""
    try:
        hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d")
        today = datetime.now()
        years = today.year - hire_date.year - ((today.month, today.day) < (hire_date.month, hire_date.day))
        months = (today.month - hire_date.month) % 12
        if years == 0:
            return f"{months} months"
        elif months == 0:
            return f"{years} years"
        else:
            return f"{years} years, {months} months"
    except Exception as e:
        print(f"Error in calculating tenure: {e}")
        return "Unknown"

def get_relevant_resource_links(question, answer=None):
    """Find relevant resource links based on question and answer content"""
    combined_text = (question + " " + (answer or "")).lower()
    
    relevant_links = []
    for keyword, url in RESOURCE_LINKS.items():
        if keyword.lower() in combined_text:
            relevant_links.append((keyword.title(), url))
    
    unique_links = []
    urls_seen = set()
    for title, url in relevant_links:
        if url not in urls_seen:
            unique_links.append((title, url))
            urls_seen.add(url)
    
    if unique_links:
        links_markdown = "**Helpful Resources:**\n"
        for title, url in unique_links[:3]:  # Limit to top 3 links
            links_markdown += f"* [{title}]({url})\n"
        return links_markdown
    
    return ""

# Function to get PDF content
def get_pdf_content():
    """Get the PDF content."""
    if "pdf_content" in st.session_state and st.session_state.pdf_content:
        return st.session_state.pdf_content
    
    pdf_files = pdf_processor.get_available_pdfs()
    if pdf_files:
        content = pdf_processor.load_pdf_content(filename=pdf_files[0])
        st.session_state.pdf_content = content
        return content
    
    return "No PDF content available."

def classify_topic(question, answer):
    """Classify message topic using OpenAI API."""
    client = get_openai_client()
    
    prompt = f"""
    Classify the following HR conversation into one of these categories:
    - Benefits
    - Policies
    - Procedures
    - Career Development
    - Compensation
    - Time Off
    - Other
    
    Question: {question}
    Answer: {answer}
    
    Category:
    """
    
    try:
        response = client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant that classifies HR conversations."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=10
        )
        
        topic = response.choices[0].message.content.strip()
        return topic
    except Exception as e:
        print(f"Error classifying topic: {e}")
        return "Other"

def generate_summary(question, answer):
    """Generate a conversation summary using OpenAI API."""
    client = get_openai_client()
    
    prompt = f"""
    Summarize the following HR conversation in one short sentence:
    
    Question: {question}
    Answer: {answer}
    
    Summary:
    """
    
    try:
        response = client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Conversation about {question[:30]}..."

def find_semantic_matches(question, pdf_content):
    """Use OpenAI to find semantically relevant sections in the PDF content"""
    client = get_openai_client()
    
    search_prompt = f"""
    Given this question from an employee: "{question}"
    
    Please identify the 3-5 most relevant sections from this HR document that contain information to answer the question.
    Consider different ways the question could be phrased and look for semantic matches, not just keyword matches.
    
    HR Document:
    {pdf_content[:15000]}  # Limit for token constraints
    
    Return the relevant sections, separated by "===SECTION===" markers.
    If you can't find any relevant information, respond with "NO_RELEVANT_CONTENT_FOUND" and suggest related topics the employee might want to ask about instead.
    """
    
    try:
        response = client.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[{"role": "user", "content": search_prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        if "NO_RELEVANT_CONTENT_FOUND" in content:
            return ""
            
        return content
    except Exception as e:
        print(f"Error finding semantic matches: {e}")
        return ""

# Function to get chatbot response
def get_chatbot_response(question, conversation_history=[]):
    client = get_openai_client()
    
    if client is None:
        return {"answer": "Error: OpenAI client not initialized.", "suggestions": [], "topic": "Error"}
    
    full_pdf_content = get_pdf_content()
    employee_data = st.session_state.employee_data
    
    relevant_content = find_semantic_matches(question, full_pdf_content)
    
    if not relevant_content:
        relevant_content = pdf_processor.get_relevant_chunks(question, full_pdf_content, num_chunks=4)
    
    system_message = f"""You are an AI HR Assistant for Valley Water. Your role is to help employees with their HR-related questions in a friendly, personalized way.
    ...
    """
    
    messages = [{"role": "system", "content": system_message}]
    for message in conversation_history[-10:]:
        messages.append(message)
    
    messages.append({"role": "user", "content": question})
    
    try:
        response = client.ChatCompletion.create(
            model="gpt-4",  
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content.strip()
        resource_links = get_relevant_resource_links(question, answer)
        if resource_links:
            answer += f"\n\n{resource_links}"
        
        suggestion_prompt = f"""
        Based on this conversation between an employee and HR:
        
        Employee question: "{question}"
        HR assistant answer: "{answer}"
        
        Generate 3 helpful follow-up questions this employee might want to ask next. These should:
        1. Build naturally on the current conversation
        2. Be relevant to someone in the {employee_data['department']} department
        3. Help the employee get more specific information or take next steps
        4. Be phrased in a casual, conversational way
        
        Each question should be a single sentence ending with a question mark.
        """
        
        suggestion_response = client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": suggestion_prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        suggestion_text = suggestion_response.choices[0].message.content.strip()
        suggestions = []
        
        for line in suggestion_text.split('\n'):
            clean_line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            if clean_line and '?' in clean_line:
                suggestions.append(clean_line)
        
        if len(suggestions) < 3:
            suggestions.extend(["How does this affect my role?", "Who do I contact?", "What's next?"])
        
        suggestions = suggestions[:3]
        
        topic = classify_topic(question, answer)
        summary = generate_summary(question, answer)
        
        db_manager.save_conversation(
            employee_id=st.session_state.employee_id,
            employee_name=employee_data['name'],
            question=question,
            answer=answer,
            summary=summary,
            topic=topic,
            conversation_id=st.session_state.conversation_id
        )
        
        return {
            "answer": answer,
            "suggestions": suggestions,
            "topic": topic
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error getting chatbot response: {error_msg}")
        return {
            "answer": f"I'm sorry, I encountered an error while processing your question. Please try again or contact HR directly for assistance.",
            "suggestions": [
                "Can you rephrase your question?",
                "Would you like to ask about something else?",
                "Would you like to speak with someone from HR directly?"
            ],
            "topic": "Error"
        }

@login_required
def main():
    # Initialize chat history, suggestions, and session state as before
    ...

# Call the main function
if __name__ == "__main__":
    main()
