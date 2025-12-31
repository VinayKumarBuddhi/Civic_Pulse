"""
Civic Pulse - Main Landing Page
Landing page with NGO details, Register/Sign-in options, and Chatbot
"""
import os
import sys
from pathlib import Path

# Suppress PyTorch/Streamlit compatibility warnings (harmless but noisy)
os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')
# Suppress TensorFlow deprecation warnings
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database.models import NGOModel
from database.database import get_ngo_collection, get_mongodb_client, get_database, DATABASE_NAME
from bson import ObjectId
from auth.authentication import login, register_user
from auth.session import login_user, logout_user, is_authenticated, get_current_role, get_current_username
from rag.vector_store import initialize_vector_store

# Page configuration
st.set_page_config(
    page_title="Civic Pulse - Community Issue Reporting",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #666;
            text-align: center;
            margin-bottom: 2rem;
        }
        .ngo-card {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background-color: #f9f9f9;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .ngo-title {
            font-size: 1.5rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 0.5rem;
        }
        .ngo-category {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.85rem;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .chatbot-container {
            border: 2px solid #1f77b4;
            border-radius: 10px;
            padding: 1.5rem;
            background-color: #f0f8ff;
            margin-top: 2rem;
        }
        .auth-section {
            background-color: #f5f5f5;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_register' not in st.session_state:
    st.session_state.show_register = False
if 'show_signin' not in st.session_state:
    st.session_state.show_signin = False
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = False
if 'mongodb_checked' not in st.session_state:
    st.session_state.mongodb_checked = False
if 'mongodb_connected' not in st.session_state:
    st.session_state.mongodb_connected = False
if 'mongodb_info' not in st.session_state:
    st.session_state.mongodb_info = None

def format_address(address_dict):
    """Format address dictionary to readable string"""
    if not address_dict:
        return "Address not available"
    parts = []
    if address_dict.get('area'):
        parts.append(address_dict['area'])
    if address_dict.get('city'):
        parts.append(address_dict['city'])
    if address_dict.get('district') or address_dict.get('dist'):
        parts.append(address_dict.get('district') or address_dict.get('dist'))
    if address_dict.get('state'):
        parts.append(address_dict['state'])
    if address_dict.get('pincode'):
        parts.append(f"PIN: {address_dict['pincode']}")
    return ", ".join(parts) if parts else "Address not available"

def display_ngo_card(ngo):
    """Display a single NGO card"""
    ngo_id = str(ngo.get('_id', ''))
    username = ngo.get('Username', 'Unknown NGO')
    description = ngo.get('Description', 'No description available.')
    categories = ngo.get('Categories', [])
    address = ngo.get('Address', {})
    location = ngo.get('Location', {})
    
    card_html = f"""
    <div class="ngo-card">
        <div class="ngo-title">{username}</div>
        <p style="margin-bottom: 1rem; color: #555;">{description}</p>
        <div style="margin-bottom: 1rem;">
    """
    
    for category in categories:
        card_html += f'<span class="ngo-category">{category}</span>'
    
    card_html += "</div>"
    card_html += f"<p style='margin-bottom: 0.5rem;'><strong>📍 Location:</strong> {format_address(address)}</p>"
    
    if location.get('latitude') and location.get('longitude'):
        card_html += f"<p style='margin-bottom: 0; font-size: 0.9rem; color: #777;'>Lat: {location['latitude']:.6f}, Long: {location['longitude']:.6f}</p>"
    
    card_html += "</div>"
    
    return card_html

def render_register_form():
    """Render user registration form"""
    st.markdown("### 📝 Register New Account")
    st.markdown("**Note:** Registration is available for Users only.")
    
    with st.form("register_form"):
        name = st.text_input("Full Name *", placeholder="Enter your full name")
        username = st.text_input("Username *", placeholder="Choose a unique username")
        email = st.text_input("Email *", placeholder="your.email@example.com")
        phone = st.text_input("Phone Number *", placeholder="10-digit phone number")
        
        st.markdown("**Address**")
        col1, col2 = st.columns(2)
        with col1:
            area = st.text_input("Area *", placeholder="Area/Locality")
            city = st.text_input("City *", placeholder="City")
            district = st.text_input("District *", placeholder="District")
        with col2:
            state = st.text_input("State *", placeholder="State")
            pincode = st.text_input("Pincode *", placeholder="PIN Code")
        
        password = st.text_input("Password *", type="password", placeholder="Create a strong password")
        confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password")
        
        submitted = st.form_submit_button("Register", use_container_width=True)
        
        if submitted:
            # Basic validation
            if not all([name, username, email, phone, area, city, district, state, pincode, password, confirm_password]):
                st.error("Please fill in all required fields marked with *")
            elif password != confirm_password:
                st.error("Passwords do not match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long")
            else:
                # Prepare address dictionary
                address = {
                    "area": area,
                    "city": city,
                    "district": district,
                    "state": state,
                    "pincode": pincode
                }
                
                # Register user
                success, error_msg = register_user(
                    name=name,
                    username=username,
                    email=email,
                    phone=phone,
                    address=address,
                    password=password
                )
                
                if success:
                    st.success("✅ Registration successful! Please sign in to continue.")
                    st.session_state.show_register = False
                    st.session_state.show_signin = True
                    st.rerun()
                else:
                    st.error(f"Registration failed: {error_msg}")

def render_signin_form():
    """Render sign-in form"""
    st.markdown("### 🔐 Sign In")
    
    with st.form("signin_form"):
        role = st.selectbox("Select Your Role *", ["User", "NGO", "Volunteer", "Admin"])
        username = st.text_input("Username *", placeholder="Enter your username")
        password = st.text_input("Password *", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("Sign In", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            elif not role:
                st.error("Please select a role")
            else:
                # Attempt login
                success, user_data, error_msg = login(username=username, password=password, role=role)
                
                if success and user_data:
                    # Set session
                    login_user(user_data, role)
                    st.success(f"✅ Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {error_msg}")

def render_chatbot():
    """Render chatbot interface"""
    st.markdown('<div class="chatbot-container">', unsafe_allow_html=True)
    st.markdown("### 💬 Civic Pulse Chatbot")
    st.markdown("Ask me anything about NGOs, issues, or civic services!")
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, (role, message) in enumerate(st.session_state.chat_history):
            if role == "user":
                st.markdown(f"**You:** {message}")
            else:
                st.markdown(f"**Bot:** {message}")
            st.markdown("---")
    
    # Chat input
    user_input = st.text_input("Type your message...", key="chat_input", placeholder="e.g., Tell me about NGOs working on environmental issues")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        send_button = st.button("Send 💬")
    
    if send_button and user_input:
        # Add user message to history
        st.session_state.chat_history.append(("user", user_input))
        
        # Placeholder response (will be replaced with RAG chatbot implementation)
        bot_response = "🤖 Chatbot functionality will be implemented in rag/chatbot.py. This is a placeholder response."
        st.session_state.chat_history.append(("bot", bot_response))
        st.rerun()
    
    # Example queries
    st.markdown("**💡 Example queries:**")
    example_queries = [
        "What NGOs are working in my area?",
        "How can I report a pothole?",
        "Tell me about environmental NGOs",
        "What is the status of issue #123?"
    ]
    for query in example_queries:
        if st.button(query, key=f"example_{query}", use_container_width=True):
            st.session_state.chat_history.append(("user", query))
            bot_response = "🤖 Chatbot implementation pending. This would show relevant NGO information and issue details."
            st.session_state.chat_history.append(("bot", bot_response))
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def initialize_app():
    """Initialize application components on startup"""
    # Ensure initialization runs only once per session
    if st.session_state.get('app_initialized'):
        return
    # Initialize vector store for RAG matching
    try:
        initialize_vector_store()
        print("✅ Vector store initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Vector store initialization failed: {str(e)}")
        print("   RAG matching may not work correctly. Check ChromaDB installation.")
    finally:
        # Mark app as initialized regardless to avoid repeated init attempts during the session
        st.session_state.app_initialized = True

def check_mongodb_connection():
    """Check MongoDB connection and print status"""
    # Run check only once per Streamlit session
    if st.session_state.get('mongodb_checked'):
        return st.session_state.get('mongodb_connected', False)

    print("=" * 50)
    print("Checking MongoDB Connection...")
    print("=" * 50)
    
    try:
        client = get_mongodb_client()
        if client:
            # Test the connection
            client.admin.command('ping')
            db = get_database()
            
            print(f"✅ MongoDB Connection: SUCCESS")
            print(f"📊 Database Name: {DATABASE_NAME}")
            print(f"🔗 Connection String: {client.address}")
            
            # Try to access a collection to verify database access
            if db is not None:
                collections = db.list_collection_names()
                print(f"📁 Available Collections: {collections if collections else 'None (Database is empty)'}")
                # Update session state so the rest of the app can read status
                st.session_state.mongodb_connected = True
                st.session_state.mongodb_info = {
                    'database': DATABASE_NAME,
                    'address': client.address,
                    'collections': collections
                }
                st.session_state.mongodb_checked = True
                print("=" * 50)
                return True
            else:
                print("❌ MongoDB Connection: FAILED - Could not access database")
                print("=" * 50)
                st.session_state.mongodb_connected = False
                st.session_state.mongodb_info = None
                st.session_state.mongodb_checked = True
                return False
        else:
            print("❌ MongoDB Connection: FAILED - Client is None")
            print("=" * 50)
            st.session_state.mongodb_connected = False
            st.session_state.mongodb_info = None
            st.session_state.mongodb_checked = True
            return False
    except Exception as e:
        print(f"❌ MongoDB Connection: FAILED")
        print(f"⚠️  Error: {str(e)}")
        print("=" * 50)
        st.session_state.mongodb_connected = False
        st.session_state.mongodb_info = {'error': str(e)}
        st.session_state.mongodb_checked = True
        return False

# Main page content
def main():

    
    # Check MongoDB connection on startup
    mongodb_connected = check_mongodb_connection()
    
    # Initialize app components (vector store, etc.)
    initialize_app()
    
    # Header
    st.markdown('<div class="main-header">🌍 Civic Pulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Community Issue Reporting & Management Platform</div>', unsafe_allow_html=True)
    
    # Display connection status in UI (optional)
    if not mongodb_connected:
        st.warning("⚠️ MongoDB connection issue detected. Check the console/terminal for details.")
    
    # Check if user is authenticated - if yes, show dashboard option
    if is_authenticated():
        current_role = get_current_role()
        current_username = get_current_username()
        
        st.success(f"✅ Logged in as **{current_username}** ({current_role})")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Go to Dashboard", use_container_width=True, type="primary"):
                # Redirect to appropriate dashboard based on role
                try:
                    if current_role == "User":
                        st.switch_page("pages/1_User_Dashboard.py")
                    elif current_role == "NGO":
                        st.switch_page("pages/2_NGO_Dashboard.py")
                    elif current_role == "Volunteer":
                        st.switch_page("pages/3_Volunteer_Dashboard.py")
                    elif current_role == "Admin":
                        st.switch_page("pages/4_Admin_Dashboard.py")
                    else:
                        st.warning("Unknown role. Please contact support.")
                except Exception as e:
                    st.info("Dashboard pages are not yet created. They will be available soon!")
        with col2:
            if st.button("Logout", use_container_width=True):
                logout_user()
                st.session_state.show_register = False
                st.session_state.show_signin = False
                st.rerun()
        
        st.markdown("---")
    
    # Authentication Section
    st.markdown('<div class="auth-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Register", use_container_width=True, type="primary"):
            st.session_state.show_register = not st.session_state.show_register
            st.session_state.show_signin = False
    
    with col2:
        if st.button("🔐 Sign In", use_container_width=True, type="secondary"):
            st.session_state.show_signin = not st.session_state.show_signin
            st.session_state.show_register = False
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show register or signin form
    if st.session_state.show_register:
        render_register_form()
        st.markdown("---")
    
    if st.session_state.show_signin:
        render_signin_form()
        st.markdown("---")
    
    # NGO Details Section
    st.markdown("## 🏢 Our Partner NGOs")
    st.markdown("Browse through our network of Non-Governmental Organizations working for the community.")
    
    # Filter section
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("🔍 Search NGOs", placeholder="Search by name, category, or location...")
    with col2:
        filter_active = st.checkbox("Active NGOs Only", value=True)
    
    # Fetch and display NGOs
    try:
        if filter_active:
            ngos = NGOModel.find_all_active()
        else:
            ngos = NGOModel.find_all()
        
        if not ngos:
            st.info("📭 No NGOs found in the database. NGOs will appear here once they are registered by Admins.")
        else:
            # Filter by search query if provided
            if search_query:
                search_lower = search_query.lower()
                ngos = [ngo for ngo in ngos if 
                       search_lower in ngo.get('Username', '').lower() or
                       search_lower in ngo.get('Description', '').lower() or
                       any(search_lower in cat.lower() for cat in ngo.get('Categories', [])) or
                       search_lower in format_address(ngo.get('Address', {})).lower()]
            
            st.markdown(f"**Found {len(ngos)} NGO(s)**")
            
            # Display NGOs in a grid
            for ngo in ngos:
                st.markdown(display_ngo_card(ngo), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error fetching NGOs: {str(e)}")
        st.info("Make sure MongoDB is running and the database connection is configured correctly.")
    
    st.markdown("---")
    
    # Chatbot Section
    render_chatbot()

if __name__ == "__main__":
    main()
