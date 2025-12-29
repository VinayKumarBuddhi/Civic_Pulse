"""
Admin Dashboard - Civic Pulse
Allows admins to manage NGOs, volunteers, monitor issues, and view system statistics
"""
import streamlit as st
import sys
from pathlib import Path
from bson import ObjectId
from datetime import datetime
import secrets
import string

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.models import ReportsModel, NGOModel, VolunteersModel, ApplicationsModel, UserModel, AdminModel
from database.database import get_reports_collection, get_ngo_collection, get_volunteers_collection, get_user_collection
from auth.session import is_authenticated, get_current_username, get_current_user, require_role, logout_user
from auth.authentication import hash_password
from database.schemas import REPORT_STATUS_ENUM, APPLICATION_STATUS_ENUM
from rag.vector_store import add_ngo_to_vector_db, update_ngo_in_vector_db, remove_ngo_from_vector_db

# Page configuration
st.set_page_config(
    page_title="Admin Dashboard - Civic Pulse",
    page_icon="👑",
    layout="wide"
)

# Common issue categories (same as User Dashboard)
ISSUE_CATEGORIES = [
    "Road & Infrastructure",
    "Water & Sanitation",
    "Environment & Pollution",
    "Healthcare",
    "Education",
    "Safety & Security",
    "Electricity",
    "Waste Management",
    "Public Transport",
    "Other"
]

# Custom CSS
st.markdown("""
    <style>
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.85rem;
            font-weight: bold;
            display: inline-block;
            margin: 0.25rem;
        }
        .status-not-verified { background-color: #ffebee; color: #c62828; }
        .status-verified { background-color: #fff3e0; color: #e65100; }
        .status-assigned { background-color: #e3f2fd; color: #1565c0; }
        .status-in-progress { background-color: #f3e5f5; color: #6a1b9a; }
        .status-resolved { background-color: #e8f5e9; color: #2e7d32; }
        .card {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            background-color: #f9f9f9;
        }
    </style>
""", unsafe_allow_html=True)

def generate_password(length=8):
    """Generate a random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def get_status_badge_html(status):
    """Get HTML for status badge"""
    status_class_map = {
        'not verified': 'status-not-verified',
        'verified': 'status-verified',
        'assigned': 'status-assigned',
        'in-progress': 'status-in-progress',
        'resolved': 'status-resolved'
    }
    status_class = status_class_map.get(status, 'status-not-verified')
    return f'<span class="status-badge {status_class}">{status.upper()}</span>'

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

def render_manage_ngos():
    """Manage NGOs - Create, View, Update, Delete"""
    st.markdown("### 🏢 Manage NGOs")
    
    # Create new NGO
    with st.expander("➕ Create New NGO Account", expanded=False):
        st.markdown("Create a new NGO account with credentials")
        
        # Initialize session state for password if not exists
        if 'admin_ngo_password' not in st.session_state:
            st.session_state.admin_ngo_password = generate_password()
        
        # Password generation button (outside form)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"💡 Auto-generated password: `{st.session_state.admin_ngo_password}`")
        with col2:
            if st.button("🔄 Generate New Password"):
                st.session_state.admin_ngo_password = generate_password()
                st.rerun()
        
        with st.form("create_ngo_form", clear_on_submit=True):
            username = st.text_input("NGO Username *", placeholder="Enter NGO username")
            password = st.text_input("Password *", type="password", value=st.session_state.admin_ngo_password, 
                                    help="Auto-generated password (you can change it)")
            
            description = st.text_area("Description *", placeholder="Describe the NGO's mission and activities...", height=100)
            
            st.markdown("**Categories (Multi-select)**")
            categories = st.multiselect("Select Categories", ISSUE_CATEGORIES, help="Select categories this NGO works with")
            
            st.markdown("**Location**")
            col1, col2 = st.columns(2)
            with col1:
                latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=0.0, step=0.000001, format="%.6f")
            with col2:
                longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=0.0, step=0.000001, format="%.6f")
            
            st.markdown("**Address**")
            col1, col2 = st.columns(2)
            with col1:
                area = st.text_input("Area/Locality")
                city = st.text_input("City")
                district = st.text_input("District")
            with col2:
                state = st.text_input("State")
                pincode = st.text_input("Pincode")
            
            is_active = st.checkbox("Active", value=True)
            
            submitted = st.form_submit_button("Create NGO Account", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password or not description:
                    st.error("Username, password, and description are required")
                else:
                    try:
                        # Check if username exists
                        existing = NGOModel.find_by_username(username)
                        if existing:
                            st.error("Username already exists. Please choose a different username.")
                        else:
                            # Hash password
                            hashed_password = hash_password(password)
                            
                            # Prepare NGO data
                            ngo_data = {
                                "Username": username,
                                "Password": hashed_password,
                                "Description": description,
                                "Categories": categories,
                                "Location": {
                                    "latitude": float(latitude),
                                    "longitude": float(longitude)
                                },
                                "Address": {
                                    "area": area,
                                    "city": city,
                                    "dist": district,  # Note: schema uses "dist" not "district"
                                    "state": state,
                                    "pincode": pincode
                                },
                                "isActive": is_active
                            }
                            
                            result = NGOModel.create_ngo(ngo_data)
                            
                            if result.inserted_id:
                                ngo_id = str(result.inserted_id)
                                # Automatically add NGO to vector DB for RAG matching
                                try:
                                    add_ngo_to_vector_db(ngo_id)
                                except Exception as vec_error:
                                    st.warning(f"⚠️ NGO created but vector DB update failed: {str(vec_error)}")
                                
                                st.success(f"✅ NGO account created successfully!")
                                st.info(f"**Username:** {username}\n\n**Password:** {password}\n\n⚠️ Please share these credentials securely with the NGO.")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Failed to create NGO account")
                    except Exception as e:
                        st.error(f"Error creating NGO: {str(e)}")
    
    # List and manage existing NGOs
    st.markdown("### 📝 Existing NGOs")
    try:
        ngos = NGOModel.find_all()
        
        if not ngos:
            st.info("📭 No NGOs registered yet. Create your first NGO account above.")
        else:
            st.markdown(f"**Total NGOs: {len(ngos)}**")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                filter_active = st.selectbox("Filter by Status", ["All", "Active Only", "Inactive Only"])
            with col2:
                search_ngo = st.text_input("🔍 Search NGO", placeholder="Search by username...")
            
            # Apply filters
            filtered_ngos = ngos
            if filter_active == "Active Only":
                filtered_ngos = [ngo for ngo in filtered_ngos if ngo.get('isActive', True)]
            elif filter_active == "Inactive Only":
                filtered_ngos = [ngo for ngo in filtered_ngos if not ngo.get('isActive', True)]
            
            if search_ngo:
                search_lower = search_ngo.lower()
                filtered_ngos = [ngo for ngo in filtered_ngos if search_lower in ngo.get('Username', '').lower()]
            
            st.markdown(f"**Showing {len(filtered_ngos)} NGO(s)**")
            st.markdown("---")
            
            for ngo in filtered_ngos:
                ngo_id = str(ngo.get('_id', ''))
                username = ngo.get('Username', 'Unknown')
                description = ngo.get('Description', 'No description')
                categories = ngo.get('Categories', [])
                is_active = ngo.get('isActive', True)
                issue_ids = ngo.get('Issues', [])
                volunteers = VolunteersModel.find_by_ngo(ngo_id)
                created_at = ngo.get('created_at', datetime.now())
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        status_text = "🟢 Active" if is_active else "🔴 Inactive"
                        st.markdown(f"**{username}** - {status_text}")
                        st.markdown(f"**Description:** {description[:100]}..." if len(description) > 100 else f"**Description:** {description}")
                        if categories:
                            category_tags = " | ".join([f"`{cat}`" for cat in categories])
                            st.markdown(f"**Categories:** {category_tags}")
                        st.markdown(f"**Location:** {format_address(ngo.get('Address', {}))}")
                        st.markdown(f"Issues: {len(issue_ids)} | Volunteers: {len(volunteers)} | Created: {created_at.strftime('%B %d, %Y') if isinstance(created_at, datetime) else 'Unknown'}")
                    with col2:
                        if st.button("Toggle Active", key=f"toggle_{ngo_id}"):
                            try:
                                ngo_collection = get_ngo_collection()
                                if ngo_collection is not None:
                                    new_active_status = not is_active
                                    ngo_collection.update_one(
                                        {"_id": ObjectId(ngo_id)},
                                        {"$set": {"isActive": new_active_status, "updated_at": datetime.now()}}
                                    )
                                    
                                    # Update vector DB based on new status
                                    try:
                                        if new_active_status:
                                            # NGO is now active, add/update in vector DB
                                            update_ngo_in_vector_db(ngo_id)
                                        else:
                                            # NGO is now inactive, remove from vector DB
                                            remove_ngo_from_vector_db(ngo_id)
                                    except Exception as vec_error:
                                        st.warning(f"⚠️ NGO status updated but vector DB update failed: {str(vec_error)}")
                                    
                                    st.success(f"NGO status updated to {'Active' if new_active_status else 'Inactive'}")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error updating NGO: {str(e)}")
                        if st.button("View Details", key=f"view_{ngo_id}"):
                            st.session_state[f"show_ngo_details_{ngo_id}"] = not st.session_state.get(f"show_ngo_details_{ngo_id}", False)
                    
                    if st.session_state.get(f"show_ngo_details_{ngo_id}", False):
                        with st.expander("NGO Details", expanded=True):
                            st.markdown(f"**Full Description:** {description}")
                            st.markdown(f"**Categories:** {', '.join(categories) if categories else 'None'}")
                            st.markdown(f"**Address:** {format_address(ngo.get('Address', {}))}")
                            location = ngo.get('Location', {})
                            if location.get('latitude') and location.get('longitude'):
                                st.markdown(f"**Coordinates:** {location['latitude']:.6f}, {location['longitude']:.6f}")
                            st.markdown(f"**Assigned Issues:** {len(issue_ids)}")
                            st.markdown(f"**Volunteers:** {len(volunteers)}")
                            st.markdown(f"**Created:** {created_at.strftime('%B %d, %Y at %I:%M %p') if isinstance(created_at, datetime) else 'Unknown'}")
                    
                    st.markdown("---")
                    
    except Exception as e:
        st.error(f"Error fetching NGOs: {str(e)}")

def render_manage_volunteers():
    """Manage volunteers across all NGOs"""
    st.markdown("### 👥 Manage Volunteers (All NGOs)")
    
    try:
        # Get all NGOs for filtering
        ngos = NGOModel.find_all()
        ngo_options = {f"{ngo.get('Username', 'Unknown')}": str(ngo.get('_id', '')) for ngo in ngos}
        
        # Filter by NGO
        selected_ngo_filter = st.selectbox("Filter by NGO", ["All NGOs"] + list(ngo_options.keys()))
        
        # Get all volunteers
        volunteers_collection = get_volunteers_collection()
        if volunteers_collection is None:
            st.error("Database connection error")
            return
        
        all_volunteers = list(volunteers_collection.find({}))
        
        # Filter volunteers
        if selected_ngo_filter != "All NGOs":
            selected_ngo_id = ngo_options.get(selected_ngo_filter)
            all_volunteers = [v for v in all_volunteers if str(v.get('NGO')) == selected_ngo_id]
        
        st.markdown(f"**Total Volunteers: {len(all_volunteers)}**")
        st.markdown("---")
        
        if not all_volunteers:
            st.info("📭 No volunteers found.")
        else:
            for volunteer in all_volunteers:
                volunteer_id = str(volunteer.get('_id', ''))
                username = volunteer.get('Username', 'Unknown')
                ngo_id = volunteer.get('NGO')
                assigned_works = volunteer.get('assignedWorks', [])
                created_at = volunteer.get('created_at', datetime.now())
                
                # Get NGO name
                ngo_name = "Unknown NGO"
                if ngo_id:
                    ngo = NGOModel.find_by_id(str(ngo_id))
                    if ngo:
                        ngo_name = ngo.get('Username', 'Unknown NGO')
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{username}**")
                        st.markdown(f"NGO: {ngo_name} | Assigned Issues: {len(assigned_works)} | Created: {created_at.strftime('%B %d, %Y') if isinstance(created_at, datetime) else 'Unknown'}")
                    with col2:
                        st.info("View only - Removal can be done from NGO dashboard")
                    
                    st.markdown("---")
                    
    except Exception as e:
        st.error(f"Error fetching volunteers: {str(e)}")

def render_monitor_issues():
    """Monitor all issues in the system"""
    st.markdown("### 📊 Monitor All Issues")
    
    try:
        reports_collection = get_reports_collection()
        if reports_collection is None:
            st.error("Database connection error")
            return
        
        all_reports = list(reports_collection.find({}))
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All"] + list(REPORT_STATUS_ENUM))
        with col2:
            search_issue = st.text_input("🔍 Search", placeholder="Search by description or reporter...")
        
        # Apply filters
        filtered_reports = all_reports
        if status_filter != "All":
            filtered_reports = [r for r in filtered_reports if r.get('Status') == status_filter]
        
        if search_issue:
            search_lower = search_issue.lower()
            filtered_reports = [r for r in filtered_reports 
                              if search_lower in r.get('Description', '').lower() or 
                                 search_lower in r.get('Username', '').lower()]
        
        # Sort by creation date (newest first)
        filtered_reports.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        st.markdown(f"**Total Issues: {len(all_reports)} | Filtered: {len(filtered_reports)}**")
        st.markdown("---")
        
        if not filtered_reports:
            st.info("📭 No issues found matching the filters.")
        else:
            for report in filtered_reports:
                report_id = str(report.get('_id', ''))
                description = report.get('Description', 'No description')
                categories = report.get('Categories', [])
                status = report.get('Status', 'not verified')
                address = report.get('Address', {})
                username = report.get('Username', 'Unknown')
                created_at = report.get('created_at', datetime.now())
                assigned_to = report.get('assignedTo', [])
                
                with st.container():
                    st.markdown(f"**Issue ID:** `{report_id[:8]}...` | **Reporter:** {username}")
                    st.markdown(get_status_badge_html(status), unsafe_allow_html=True)
                    st.markdown(f"**Reported on:** {created_at.strftime('%B %d, %Y at %I:%M %p') if isinstance(created_at, datetime) else 'Unknown'}")
                    
                    st.markdown(f"**Description:** {description[:200]}..." if len(description) > 200 else f"**Description:** {description}")
                    
                    if categories:
                        category_tags = " | ".join([f"`{cat}`" for cat in categories])
                        st.markdown(f"**Categories:** {category_tags}")
                    
                    st.markdown(f"**Location:** {format_address(address)}")
                    
                    # Show assigned NGO/volunteers
                    if assigned_to:
                        assigned_info = []
                        for assigned_id in assigned_to:
                            try:
                                # Check if it's an NGO
                                ngo = NGOModel.find_by_id(str(assigned_id))
                                if ngo:
                                    assigned_info.append(f"🏢 NGO: {ngo.get('Username', 'Unknown')}")
                                else:
                                    # Check if it's a volunteer
                                    volunteer = VolunteersModel.find_by_username(str(assigned_id))
                                    if not volunteer:
                                        volunteers_collection_temp = get_volunteers_collection()
                                        if volunteers_collection_temp is not None:
                                            volunteer = volunteers_collection_temp.find_one({"_id": ObjectId(assigned_id)})
                                    if volunteer:
                                        assigned_info.append(f"👤 Volunteer: {volunteer.get('Username', 'Unknown')}")
                            except:
                                pass
                        if assigned_info:
                            st.markdown(f"**Assigned To:** {', '.join(assigned_info)}")
                    
                    st.markdown("---")
                    
    except Exception as e:
        st.error(f"Error fetching issues: {str(e)}")

def render_statistics():
    """Display system-wide statistics"""
    st.markdown("### 📈 System Statistics")
    
    try:
        # Get all data
        ngos = NGOModel.find_all()
        reports_collection = get_reports_collection()
        volunteers_collection = get_volunteers_collection()
        users_collection = get_user_collection()
        
        # Count users
        total_users = 0
        if users_collection is not None:
            total_users = users_collection.count_documents({})
        
        # Count volunteers
        total_volunteers = 0
        if volunteers_collection is not None:
            total_volunteers = volunteers_collection.count_documents({})
        
        # Count reports and status breakdown
        status_counts = {
            'not verified': 0,
            'verified': 0,
            'assigned': 0,
            'in-progress': 0,
            'resolved': 0
        }
        total_reports = 0
        if reports_collection is not None:
            total_reports = reports_collection.count_documents({})
            for status in status_counts.keys():
                status_counts[status] = reports_collection.count_documents({"Status": status})
        
        # Count active/inactive NGOs
        active_ngos = len([ngo for ngo in ngos if ngo.get('isActive', True)])
        inactive_ngos = len(ngos) - active_ngos
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", total_users)
        with col2:
            st.metric("Total NGOs", len(ngos))
            st.caption(f"Active: {active_ngos} | Inactive: {inactive_ngos}")
        with col3:
            st.metric("Total Volunteers", total_volunteers)
        with col4:
            st.metric("Total Issues", total_reports)
        
        st.markdown("---")
        
        # Issue status breakdown
        st.markdown("**Issue Status Breakdown:**")
        col1, col2 = st.columns(2)
        with col1:
            for status, count in list(status_counts.items())[:3]:
                st.markdown(f"- {status.replace('-', ' ').title()}: {count}")
        with col2:
            for status, count in list(status_counts.items())[3:]:
                st.markdown(f"- {status.replace('-', ' ').title()}: {count}")
        
        st.markdown("---")
        
        # NGO activity
        st.markdown("**NGO Activity:**")
        ngo_issue_counts = {}
        for ngo in ngos:
            issue_count = len(ngo.get('Issues', []))
            ngo_issue_counts[ngo.get('Username', 'Unknown')] = issue_count
        
        # Sort NGOs by issue count (descending)
        sorted_ngos = sorted(ngo_issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_ngos:
            st.markdown("Top 10 NGOs by assigned issues:")
            for ngo_name, count in sorted_ngos:
                st.markdown(f"- {ngo_name}: {count} issues")
        else:
            st.info("No NGO activity data available")
        
    except Exception as e:
        st.error(f"Error fetching statistics: {str(e)}")

def main():
    # Check authentication
    if not is_authenticated():
        st.error("❌ You must be logged in to access this page.")
        st.info("Please go to the main page and sign in.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Check role
    if not require_role("Admin"):
        current_role = st.session_state.get('user_role', 'Unknown')
        st.error(f"❌ Access denied. This page is for Admins only. Your role: {current_role}")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get current admin
    username = get_current_username()
    
    if not username:
        st.error("❌ User session error. Please log in again.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Header
    st.title("👑 Admin Dashboard")
    st.markdown(f"Welcome, **{username}**!")
    st.markdown("Manage NGOs, volunteers, monitor issues, and view system statistics")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Navigation")
        if st.button("🏠 Go to Home"):
            st.switch_page("app.py")
        if st.button("🚪 Logout"):
            logout_user()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Stats")
        try:
            ngos = NGOModel.find_all()
            reports_collection = get_reports_collection()
            total_reports = 0
            if reports_collection is not None:
                total_reports = reports_collection.count_documents({})
            st.metric("Total NGOs", len(ngos))
            st.metric("Total Issues", total_reports)
        except Exception as e:
            st.info("Stats not available")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 Manage NGOs", "👥 Manage Volunteers", "📊 Monitor Issues", "📈 Statistics"])
    
    with tab1:
        render_manage_ngos()
    
    with tab2:
        render_manage_volunteers()
    
    with tab3:
        render_monitor_issues()
    
    with tab4:
        render_statistics()

if __name__ == "__main__":
    main()

