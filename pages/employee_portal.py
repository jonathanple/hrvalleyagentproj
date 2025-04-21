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
    # Get API key from environment or secrets
    api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key", "")
    
    if not api_key:
        st.warning("OpenAI API key not found. Chatbot functionality will be limited.")
        # Replace with your actual OpenAI API key
        openai.api_key = api_key
    # Print the first few characters of the key being used (for debugging)
    print(f"Using API key starting with: {api_key[:8]}...")
    
    return openai

# Resource links database
RESOURCE_LINKS = {
    # Benefits
    "health insurance": "https://valleywater.org/employee/benefits/health-insurance",
    "dental insurance": "https://valleywater.org/employee/benefits/dental-insurance",
    "vision insurance": "https://valleywater.org/employee/benefits/vision-care",
    "retirement": "https://valleywater.org/employee/benefits/retirement-plans",
    "401k": "https://valleywater.org/employee/benefits/retirement-plans",
    "pension": "https://valleywater.org/employee/benefits/retirement-plans",
    
    # Time Off
    "pto": "https://valleywater.org/employee/time-off/paid-time-off",
    "vacation": "https://valleywater.org/employee/time-off/vacation",
    "sick leave": "https://valleywater.org/employee/time-off/sick-leave",
    "holidays": "https://valleywater.org/employee/time-off/holidays",
    "bereavement": "https://valleywater.org/employee/time-off/bereavement",
    "family leave": "https://valleywater.org/employee/time-off/family-leave",
    
    # Policies
    "employee handbook": "https://valleywater.org/employee/policies/handbook",
    "dress code": "https://valleywater.org/employee/policies/dress-code",
    "code of conduct": "https://valleywater.org/employee/policies/code-of-conduct",
    "remote work": "https://valleywater.org/employee/policies/remote-work",
    
    # Procedures
    "performance review": "https://valleywater.org/employee/procedures/performance-reviews",
    "expense reimbursement": "https://valleywater.org/employee/procedures/expenses",
    "training": "https://valleywater.org/employee/procedures/training-development",
    
    # Departments
    "engineering": "https://valleywater.org/departments/engineering",
    "human resources": "https://valleywater.org/departments/human-resources",
    "finance": "https://valleywater.org/departments/finance",
    "operations": "https://valleywater.org/departments/operations",
    "it": "https://valleywater.org/departments/information-technology",
    "legal": "https://valleywater.org/departments/legal",
    
    # General
    "directory": "https://valleywater.org/employee/directory",
    "contact hr": "https://valleywater.org/employee/contact/human-resources",
    "forms": "https://valleywater.org/employee/forms"
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
    except:
        return "Unknown"

def get_relevant_resource_links(question, answer=None):
    """Find relevant resource links based on question and answer content"""
    combined_text = (question + " " + (answer or "")).lower()
    
    # Find matching links
    relevant_links = []
    for keyword, url in RESOURCE_LINKS.items():
        if keyword.lower() in combined_text:
            relevant_links.append((keyword.title(), url))
    
    # Remove duplicates (keeping the first occurrence)
    unique_links = []
    urls_seen = set()
    for title, url in relevant_links:
        if url not in urls_seen:
            unique_links.append((title, url))
            urls_seen.add(url)
    
    # Format links as markdown
    if unique_links:
        links_markdown = "**Helpful Resources:**\n"
        for title, url in unique_links[:3]:  # Limit to top 3 links
            links_markdown += f"* [{title}]({url})\n"
        return links_markdown
    
    return ""

# Function to get PDF content
def get_pdf_content():
    # If content already in session state, return it
    if "pdf_content" in st.session_state and st.session_state.pdf_content:
        return st.session_state.pdf_content
    
    # Otherwise load default PDFs
    pdf_files = pdf_processor.get_available_pdfs()
    if pdf_files:
        # Load the first available PDF
        content = pdf_processor.load_pdf_content(filename=pdf_files[0])
        st.session_state.pdf_content = content
        return content
    
    return "No PDF content available."

# Function to classify message topic
def classify_topic(question, answer):
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
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies HR conversations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        topic = response.choices[0].message.content.strip()
        return topic
    except Exception as e:
        print(f"Error classifying topic: {e}")
        return "Other"

# Function to generate conversation summary
def generate_summary(question, answer):
    client = get_openai_client()
    
    prompt = f"""
    Summarize the following HR conversation in one short sentence:
    
    Question: {question}
    Answer: {answer}
    
    Summary:
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely."},
                {"role": "user", "content": prompt}
            ],
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
    If the exact information isn't present, identify sections with related information that could help address the question.
    
    HR Document:
    {pdf_content[:15000]}  # Limit for token constraints
    
    Return the relevant sections, separated by "===SECTION===" markers.
    If you can't find any relevant information, respond with "NO_RELEVANT_CONTENT_FOUND" and suggest related topics the employee might want to ask about instead.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",  # Using larger context model for search
            messages=[{"role": "user", "content": search_prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Check if no relevant content was found
        if "NO_RELEVANT_CONTENT_FOUND" in content:
            # Return empty string to trigger fallback
            return ""
            
        return content
    except Exception as e:
        print(f"Error finding semantic matches: {e}")
        return ""

# Function to get chatbot response
def get_chatbot_response(question, conversation_history=[]):
    client = get_openai_client()
    
    # Get full PDF content
    full_pdf_content = get_pdf_content()
    
    # Get employee data from session state
    employee_data = st.session_state.employee_data
    
    # Step 1: Use semantic search to find relevant content
    relevant_content = find_semantic_matches(question, full_pdf_content)
    
    # If no relevant content found through semantic search, use fallback method
    if not relevant_content:
        # Use the more general chunk-based approach as fallback
        relevant_content = pdf_processor.get_relevant_chunks(question, full_pdf_content, num_chunks=4)
    
    # Step 2: Create a personalized, conversational system message
    system_message = f"""You are an AI HR Assistant for Valley Water. Your role is to help employees with their HR-related questions in a friendly, personalized way.

Your response should be:
1. CONVERSATIONAL and FRIENDLY - talk like a helpful HR colleague would, not a policy manual
2. EASY TO READ - use simple language, clear headings, and bullet points
3. PERSONALIZED - refer to the employee's specific situation (name, department, tenure, etc.)
4. HELPFUL - include practical next steps when appropriate
5. COMPREHENSIVE - if the exact answer isn't in the documents, use reasonable inference and general HR knowledge

About the employee you're helping:
- Name: {employee_data['name']}
- Position: {employee_data['position']}
- Department: {employee_data['department']}
- Tenure: {calculate_tenure(employee_data['hire_date'])}
- Manager: {employee_data.get('manager', 'Not specified')}
- PTO Balance: {employee_data['pto_balance']} days
- Next Review: {employee_data['next_review_date']}
- Benefits Enrolled: {', '.join(employee_data.get('enrolled_benefits', []))}

Here is the relevant information from our HR documents:

{relevant_content}

Today's date is {datetime.now().strftime('%B %d, %Y')}.

Important guidelines:
1. If you find the answer in the documents, reformulate it in a conversational, easy-to-understand way - NEVER say "I don't have information" if you can make a reasonable inference
2. Start with a direct answer to the question, then provide details
3. Use emoji occasionally to make your response engaging (1-2 emoji max)
4. Address the employee by their first name at least once
5. When appropriate, explain how policies specifically affect THIS employee based on their position/department
6. If you're not 100% certain, you can say "Based on my understanding..." rather than refusing to answer
7. Format your response with headings and bullet points when appropriate for readability
"""
    
    # Prepare conversation history for API
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    # Add relevant conversation history (last 10 exchanges max)
    for message in conversation_history[-10:]:
        messages.append(message)
    
    # Add current question
    messages.append({"role": "user", "content": question})
    
    try:
        # Step 3: Get main response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4",  # Using most capable model for best responses
            messages=messages,
            temperature=0.7,  # Higher temperature for more conversational tone
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Step 4: Identify and add relevant resource links
        resource_links = get_relevant_resource_links(question, answer)
        if resource_links:
            answer += f"\n\n{resource_links}"
        
        # Step 5: Generate custom follow-up questions based on the conversation
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
        
        suggestion_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": suggestion_prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        # Extract and clean suggestions
        suggestion_text = suggestion_response.choices[0].message.content.strip()
        suggestions = []
        
        # Process each line looking for questions
        for line in suggestion_text.split('\n'):
            # Remove numbering and bullet points
            clean_line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            clean_line = re.sub(r'^[-*•]\s*', '', clean_line).strip()
            
            # Only keep lines that are questions
            if clean_line and '?' in clean_line:
                suggestions.append(clean_line)
        
        # Ensure we have exactly 3 suggestions
        if len(suggestions) < 3:
            # If less than 3, add generic but relevant questions
            default_suggestions = [
                f"How does this affect my specific role in {employee_data['department']}?",
                "Who should I contact for more information about this?",
                "What's the next step I should take?"
            ]
            suggestions.extend(default_suggestions[:(3-len(suggestions))])
        
        # Trim to exactly 3 suggestions
        suggestions = suggestions[:3]
        
        # Step 6: Generate topic and summary for database
        topic = classify_topic(question, answer)
        summary = generate_summary(question, answer)
        
        # Step 7: Save the conversation to the database with conversation ID
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
    # Clear cached resources to ensure we use the latest API key
    if 'first_load' not in st.session_state:
        st.cache_resource.clear()
        st.session_state.first_load = True
    
    # Logout button
    if st.button("Logout", key="logout_btn", help="Logout from the HR portal"):
        logout_user()
        st.switch_page("pages/login.py")
    
    # Get employee data from session
    employee_data = st.session_state.employee_data
    
    # Initialize chat history if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Initialize suggestions if not exists
    if "suggestions" not in st.session_state:
        st.session_state.suggestions = [
            "What benefits am I eligible for?",
            "How do I request time off?",
            "When is my next performance review?"
        ]
    
    # Initialize conversation ID if not exists
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = f"{st.session_state.employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sidebar with employee profile
    with st.sidebar:
        st.markdown("<div class='profile-container'>", unsafe_allow_html=True)
        
        # Profile picture
        st.markdown("<div class='profile-pic'>", unsafe_allow_html=True)
        st.image("https://via.placeholder.com/150", width=150)  # Replace with actual profile picture
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Employee info
        st.subheader(employee_data['name'])
        st.write(f"**Position:** {employee_data['position']}")
        st.write(f"**Department:** {employee_data['department']}")
        
        if employee_data.get('manager'):
            st.write(f"**Manager:** {employee_data['manager']}")
        
        # Quick stats
        st.divider()
        st.subheader("Quick Stats")
        
        col1, col2 = st.columns(2)
        col1.metric("PTO Balance", f"{employee_data['pto_balance']} days")
        col2.metric("Next Review", employee_data['next_review_date'])
        
        # Benefits enrollment
        st.divider()
        st.subheader("My Benefits")
        
        for benefit in employee_data['enrolled_benefits']:
            st.write(f"✅ {benefit}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # New conversation button
        if st.button("Start New Conversation", key="new_conversation_btn"):
            # Generate a new conversation ID
            st.session_state.conversation_id = f"{st.session_state.employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            # Clear messages
            st.session_state.messages = []
            st.success("Started a new conversation thread!")
            time.sleep(1)
            st.rerun()
        
        # PDF document management
        st.subheader("HR Documents")
        
        # Show available PDFs
        pdf_files = pdf_processor.get_available_pdfs()
        if pdf_files:
            selected_pdf = st.selectbox("Select a document:", pdf_files)
            if st.button("Load Document", key="load_doc_btn"):
                with st.spinner("Loading document..."):
                    content = pdf_processor.load_pdf_content(filename=selected_pdf)
                    st.session_state.pdf_content = content
                    st.success(f"Loaded {selected_pdf} ({len(content)} characters)")
        else:
            st.info("No HR documents available. Please upload one.")
        
        # Upload new PDF
        uploaded_file = st.file_uploader("Upload HR Document", type="pdf")
        if uploaded_file:
            if st.button("Save & Load", key="save_load_btn"):
                with st.spinner("Processing document..."):
                    file_path = pdf_processor.save_uploaded_pdf(uploaded_file)
                    if file_path:
                        content = pdf_processor.load_pdf_content(filename=os.path.basename(file_path))
                        st.session_state.pdf_content = content
                        st.success(f"Document saved and loaded ({len(content)} characters)")
                    else:
                        st.error("Failed to save document")
    
    # Main content area
    st.markdown("<h1 class='main-title'>Valley Water HR Assistant</h1>", unsafe_allow_html=True)
    
    # Debug info - can be removed in production
    # st.caption(f"Conversation ID: {st.session_state.conversation_id}")
    
    # Welcome message on first load
    if not st.session_state.messages:
        first_name = employee_data['name'].split()[0]
        welcome_message = f"Hi {first_name}! 👋 I'm your Valley Water HR Assistant. How can I help you today? You can ask me about your benefits, time off, company policies, or anything else HR-related."
        st.session_state.messages.append({"role": "assistant", "content": welcome_message})
    
    # Display chat messages
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Process and display message content with proper formatting
            if message["role"] == "assistant":
                # Convert markdown links to HTML with the resource-link class
                content = message["content"]
                # Replace markdown headings with styled ones
                content = re.sub(r'###\s+(.+)', r'<div class="chat-header">### \1</div>', content)
                content = re.sub(r'##\s+(.+)', r'<div class="chat-header">## \1</div>', content)
                content = re.sub(r'#\s+(.+)', r'<div class="chat-header"># \1</div>', content)
                
                # Display with HTML formatting
                st.markdown(content, unsafe_allow_html=True)
            else:
                # Display user messages normally
                st.write(message["content"])
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Suggestion buttons (only show if last message was from assistant)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.write("**Suggested questions:**")
        
        # Simple solution - use a single button for each suggestion
        if st.button(st.session_state.suggestions[0], key=f"sugg_0"):
            # Process the clicked suggestion
            handle_suggestion_click(st.session_state.suggestions[0])
            
        if st.button(st.session_state.suggestions[1], key=f"sugg_1"):
            # Process the clicked suggestion
            handle_suggestion_click(st.session_state.suggestions[1])
            
        if st.button(st.session_state.suggestions[2], key=f"sugg_2"):
            # Process the clicked suggestion
            handle_suggestion_click(st.session_state.suggestions[2])
    
    # Input box for user messages
    user_input = st.chat_input("Ask your HR question here...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get chatbot response
        with st.spinner("Thinking..."):
            # Format conversation history
            history = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in st.session_state.messages[:-1]  # Exclude the latest message
            ]
            
            # Get response
            response_data = get_chatbot_response(user_input, history)
            
            # Add assistant response
            st.session_state.messages.append({"role": "assistant", "content": response_data["answer"]})
            
            # Update suggestions
            st.session_state.suggestions = response_data["suggestions"]
        
        # Rerun to update UI
        st.rerun()
    
    # Footer
    st.markdown("<div class='footer'>© 2025 Valley Water HR Assistant | Developed by Team Sapphire</div>", unsafe_allow_html=True)

# Helper function to handle suggestion clicks
def handle_suggestion_click(suggestion_text):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": suggestion_text})
    
    # Get chatbot response
    with st.spinner("Thinking..."):
        # Format conversation history
        history = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in st.session_state.messages[:-1]  # Exclude the latest message
        ]
        
        # Get response
        response_data = get_chatbot_response(suggestion_text, history)
        
        # Add assistant response
        st.session_state.messages.append({"role": "assistant", "content": response_data["answer"]})
        
        # Update suggestions
        st.session_state.suggestions = response_data["suggestions"]
    
    # Force a rerun to update the UI
    st.rerun()

if __name__ == "__main__":
    main()
