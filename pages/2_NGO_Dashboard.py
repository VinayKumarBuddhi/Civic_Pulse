"""
NGO Dashboard - Civic Pulse
Allows NGOs to manage assigned issues, volunteers, and review work updates
"""
import streamlit as st
import sys
from pathlib import Path
from bson import ObjectId
from datetime import datetime
import secrets
import string
import base64
from PIL import Image
import io

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.models import ReportsModel, NGOModel, VolunteersModel, ApplicationsModel, UserModel
from database.database import get_reports_collection, get_ngo_collection, get_volunteers_collection
from auth.session import is_authenticated, get_current_username, get_current_user, require_role, logout_user, get_current_user
from auth.authentication import hash_password
from database.schemas import REPORT_STATUS_ENUM, APPLICATION_STATUS_ENUM

# Page configuration
st.set_page_config(
    page_title="NGO Dashboard - Civic Pulse",
    page_icon="🏢",
    layout="wide"
)

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
        .issue-card {
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

def assign_issue_to_volunteer(report_id: str, volunteer_id: str, ngo_id: str):
    """Assign an issue to a volunteer"""
    try:
        reports_collection = get_reports_collection()
        volunteers_collection = get_volunteers_collection()
        
        if reports_collection is None or volunteers_collection is None:
            return False, "Database connection error"
        
        report_obj_id = ObjectId(report_id)
        volunteer_obj_id = ObjectId(volunteer_id)
        ngo_obj_id = ObjectId(ngo_id)
        
        # Update report: add NGO and volunteer to assignedTo
        report = reports_collection.find_one({"_id": report_obj_id})
        if not report:
            return False, "Report not found"
        
        assigned_to = report.get('assignedTo', [])
        if ngo_obj_id not in assigned_to:
            assigned_to.append(ngo_obj_id)
        if volunteer_obj_id not in assigned_to:
            assigned_to.append(volunteer_obj_id)
        
        reports_collection.update_one(
            {"_id": report_obj_id},
            {"$set": {"assignedTo": assigned_to, "Status": "assigned", "updated_at": datetime.now()}}
        )
        
        # Update volunteer: add report to assignedWorks
        volunteer = volunteers_collection.find_one({"_id": volunteer_obj_id})
        if volunteer:
            assigned_works = volunteer.get('assignedWorks', [])
            if report_obj_id not in assigned_works:
                assigned_works.append(report_obj_id)
                volunteers_collection.update_one(
                    {"_id": volunteer_obj_id},
                    {"$set": {"assignedWorks": assigned_works, "updated_at": datetime.now()}}
                )
        
        return True, "Issue assigned successfully"
    except Exception as e:
        return False, f"Error assigning issue: {str(e)}"

def render_assigned_issues(ngo_id: str, ngo_username: str):
    """Display issues assigned to this NGO"""
    st.markdown("### 📋 Assigned Issues")
    
    try:
        ngo = NGOModel.find_by_id(ngo_id)
        if not ngo:
            st.error("NGO not found")
            return
        
        issue_ids = ngo.get('Issues', [])
        
        if not issue_ids:
            st.info("📭 No issues assigned to your NGO yet.")
            return
        
        # Fetch all assigned reports
        reports_collection = get_reports_collection()
        if reports_collection is None:
            st.error("Database connection error")
            return
        
        reports = []
        for issue_id in issue_ids:
            report = reports_collection.find_one({"_id": ObjectId(issue_id)})
            if report:
                reports.append(report)
        
        # Sort by creation date (newest first)
        reports.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        st.markdown(f"**Total Assigned Issues: {len(reports)}**")
        st.markdown("---")
        
        for report in reports:
            report_id = str(report.get('_id', ''))
            description = report.get('Description', 'No description')
            categories = report.get('Categories', [])
            status = report.get('Status', 'not verified')
            address = report.get('Address', {})
            location = report.get('Location', {})
            created_at = report.get('created_at', datetime.now())
            assigned_to = report.get('assignedTo', [])
            username = report.get('Username', 'Unknown')
            image = report.get('Image', '')
            work_review = report.get('workReview')
            resolved_image = report.get('resolvedImage')
            
            # Format date
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%B %d, %Y at %I:%M %p")
            else:
                date_str = "Date not available"
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Issue ID:** `{report_id[:8]}...` | **Reported by:** {username}")
                    st.markdown(get_status_badge_html(status), unsafe_allow_html=True)
                    st.markdown(f"**Reported on:** {date_str}")
                with col2:
                    # Status update dropdown
                    new_status = st.selectbox(
                        "Update Status",
                        REPORT_STATUS_ENUM,
                        index=REPORT_STATUS_ENUM.index(status) if status in REPORT_STATUS_ENUM else 0,
                        key=f"status_{report_id}"
                    )
                    if new_status != status:
                        if st.button("Update Status", key=f"update_status_{report_id}"):
                            try:
                                ReportsModel.update_status(report_id, new_status)
                                st.success(f"Status updated to {new_status}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating status: {str(e)}")
                
                st.markdown(f"**Description:** {description}")
                
                if categories:
                    category_tags = " | ".join([f"`{cat}`" for cat in categories])
                    st.markdown(f"**Categories:** {category_tags}")
                
                st.markdown(f"**Location:** {format_address(address)}")
                if location.get('latitude') and location.get('longitude'):
                    st.markdown(f"📍 Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}")
                
                # Show assigned volunteers
                volunteers_list = []
                volunteers_collection = get_volunteers_collection()
                for assigned_id in assigned_to:
                    try:
                        # Skip NGO ID (we know this is the current NGO)
                        if isinstance(assigned_id, ObjectId):
                            # Check if it's a volunteer by ID
                            if volunteers_collection:
                                volunteer = volunteers_collection.find_one({"_id": assigned_id})
                                if volunteer:
                                    volunteers_list.append(volunteer.get('Username', 'Unknown'))
                    except:
                        pass
                
                if volunteers_list:
                    st.markdown(f"**Assigned Volunteers:** {', '.join(volunteers_list)}")
                
                # Assign to volunteer section
                st.markdown("**Assign to Volunteer:**")
                volunteers = VolunteersModel.find_by_ngo(ngo_id)
                if volunteers:
                    volunteer_options = {vol.get('Username', f"Volunteer {str(vol.get('_id', ''))[:8]}"): str(vol.get('_id', '')) 
                                        for vol in volunteers}
                    selected_volunteer = st.selectbox(
                        "Select Volunteer",
                        list(volunteer_options.keys()) + ["None"],
                        key=f"assign_vol_{report_id}"
                    )
                    if selected_volunteer != "None":
                        if st.button("Assign Issue", key=f"assign_{report_id}"):
                            volunteer_id = volunteer_options.get(selected_volunteer)
                            if volunteer_id:
                                success, msg = assign_issue_to_volunteer(report_id, volunteer_id, ngo_id)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                else:
                    st.info("No volunteers available. Create volunteers in the 'Manage Volunteers' tab.")
                
                # Show work review and resolved image if available
                if work_review:
                    st.markdown(f"**Work Review:** {work_review}")
                if resolved_image:
                    st.markdown("**Resolved Image:**")
                    try:
                        st.image(resolved_image, width=300)
                    except:
                        st.info("Resolved image not available")
                
                # Display original image
                if image:
                    st.markdown("**Original Issue Image:**")
                    try:
                        st.image(image, width=300)
                    except:
                        st.info("Image not available")
                
                st.markdown("---")
                
    except Exception as e:
        st.error(f"Error fetching issues: {str(e)}")

def render_manage_volunteers(ngo_id: str):
    """Manage volunteers - view and remove (volunteers come from accepted applications)"""
 
    # List existing volunteers
    st.markdown("### 📝 Existing Volunteers")
    st.info("💡 Volunteers are added automatically when you accept their applications. They use their user account credentials to login.")

    try:
        volunteers = VolunteersModel.find_by_ngo(ngo_id)
        
        if not volunteers:
            st.info("📭 No volunteers yet. Volunteers will appear here after you accept their applications in the 'Applications' tab.")
        else:
            st.markdown(f"**Total Volunteers: {len(volunteers)}**")
            
            for volunteer in volunteers:
                volunteer_id = str(volunteer.get('_id', ''))
                username = volunteer.get('Username', 'Unknown')
                assigned_works = volunteer.get('assignedWorks', [])
                created_at = volunteer.get('created_at', datetime.now())
                
                # Get user details
                user = UserModel.find_by_username(username)
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{username}**")
                        if user:
                            st.markdown(f"**Name:** {user.get('Name', 'Unknown')} | **Email:** {user.get('Email', 'Unknown')}")
                            st.markdown(f"**Phone:** {user.get('Phone number', 'Unknown')} | **Address:** {format_address(user.get('Address', {}))}")
                        st.markdown(f"**Assigned Issues:** {len(assigned_works)} | **Joined:** {created_at.strftime('%B %d, %Y') if isinstance(created_at, datetime) else 'Unknown'}")
                    with col2:
                        if st.button("Remove", key=f"remove_vol_{volunteer_id}", type="secondary"):
                            try:
                                # Remove volunteer from volunteers collection
                                VolunteersModel.delete_volunteer(volunteer_id)
                                
                                
                                # Find and revert application status to pending
                                application = ApplicationsModel.find_by_username_and_ngo(username, ngo_id)
                                if application:
                                    app_id = str(application.get('_id', ''))
                                    ApplicationsModel.update_status(app_id, 'pending')
                                
                                st.success(f"✅ Volunteer {username} removed successfully. Application status reverted to pending.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error removing volunteer: {str(e)}")
                    
                    st.markdown("---")
                    
    except Exception as e:
        st.error(f"Error fetching volunteers: {str(e)}")

def render_volunteer_applications(ngo_id: str):
    """Review and manage volunteer applications from users"""
    st.markdown("### 📨 Volunteer Applications")
    
    try:
        applications = ApplicationsModel.find_by_ngo(ngo_id)
        
        if not applications:
            st.info("📭 No volunteer applications received yet.")
            return
        
        # Filter by status
        status_filter = st.selectbox("Filter by Status", ["All"] + list(APPLICATION_STATUS_ENUM))
        
        filtered_applications = applications
        if status_filter != "All":
            filtered_applications = [app for app in applications if app.get('status') == status_filter]
        
        st.markdown(f"**Total Applications: {len(filtered_applications)}**")
        st.markdown("---")
        
        for application in filtered_applications:
            app_id = str(application.get('_id', ''))
            username = application.get('Username', 'Unknown')
            description = application.get('Description', 'No description')
            status = application.get('status', 'pending')
            created_at = application.get('created_at', datetime.now())
            #with username retrieve all the detailes of the user and display them
            user = UserModel.find_by_username(username)
            if user:
                st.markdown(f"**Name:** {user.get('Name', 'Unknown')}")
                st.markdown(f"**Email:** {user.get('Email', 'Unknown')}")
                st.markdown(f"**Phone Number:** {user.get('Phone number', 'Unknown')}")
                st.markdown(f"**Address:** {format_address(user.get('Address', {}))}")
            else:
                st.error("User not found")
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Applicant:** {username}")
                    st.markdown(f"**Status:** {status.upper()}")
                    st.markdown(f"**Applied on:** {created_at.strftime('%B %d, %Y') if isinstance(created_at, datetime) else 'Unknown'}")
                    st.markdown(f"**Application:** {description}")
                with col2:
                    if status == 'pending':
                        if st.button("Accept", key=f"accept_{app_id}", type="primary"):
                            try:
                                if not user:
                                    st.error("User not found. Cannot create volunteer account.")
                                else:
                                    # Check if volunteer already exists
                                    existing_volunteer = VolunteersModel.find_by_username(username)
                                    if existing_volunteer:
                                        st.warning(f"Volunteer {username} already exists. Application will be marked as accepted.")
                                    else:
                                        # Create volunteer with user's password (already hashed)
                                        volunteer_result = VolunteersModel.create_volunteer({
                                            "Username": username,
                                            "Password": user.get('Password'),  # Use user's existing hashed password
                                            "NGO": ngo_id
                                        })
                                        

                                    # Update application status to accepted
                                    ApplicationsModel.update_status(app_id, 'accepted')
                                    st.success(f"✅ Application accepted! {username} is now a volunteer.")
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error accepting application: {str(e)}")
                        if st.button("Reject", key=f"reject_{app_id}"):
                            try:
                                ApplicationsModel.update_status(app_id, 'rejected')
                                st.success("Application rejected")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        st.info(f"Status: {status}")
                
                st.markdown("---")
                
    except Exception as e:
        st.error(f"Error fetching applications: {str(e)}")

def render_statistics(ngo_id: str):
    """Display NGO statistics"""
    st.markdown("### 📊 Statistics")
    
    try:
        ngo = NGOModel.find_by_id(ngo_id)
        if ngo is None:
            return
        
        issue_ids = ngo.get('Issues', [])
        volunteers = VolunteersModel.find_by_ngo(ngo_id)
        applications = ApplicationsModel.find_by_ngo(ngo_id)
        
        # Get report status counts
        reports_collection = get_reports_collection()
        status_counts = {
            'not verified': 0,
            'verified': 0,
            'assigned': 0,
            'in-progress': 0,
            'resolved': 0
        }
        
        if reports_collection is not None:
            for issue_id in issue_ids:
                report = reports_collection.find_one({"_id": ObjectId(issue_id)})
                if report:
                    status = report.get('Status', 'not verified')
                    if status in status_counts:
                        status_counts[status] += 1
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issues", len(issue_ids))
        with col2:
            st.metric("Active Volunteers", len(volunteers))
        with col3:
            st.metric("Pending Applications", len([a for a in applications if a.get('status') == 'pending']))
        with col4:
            st.metric("Resolved Issues", status_counts['resolved'])
        
        st.markdown("---")
        st.markdown("**Issue Status Breakdown:**")
        for status, count in status_counts.items():
            st.markdown(f"- {status.replace('-', ' ').title()}: {count}")
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
    if not require_role("NGO"):
        current_role = st.session_state.get('user_role', 'Unknown')
        st.error(f"❌ Access denied. This page is for NGOs only. Your role: {current_role}")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get current NGO
    username = get_current_username()
    user_data = get_current_user()
    
    if not username or not user_data:
        st.error("❌ User session error. Please log in again.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get NGO ID
    ngo_id = str(user_data.get('_id', ''))
    if not ngo_id:
        st.error("❌ NGO ID not found in session.")
        return
    
    # Header
    st.title("🏢 NGO Dashboard")
    st.markdown(f"Welcome, **{username}**!")
    
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
            ngo = NGOModel.find_by_id(ngo_id)
            if ngo:
                issue_ids = ngo.get('Issues', [])
                volunteers = VolunteersModel.find_by_ngo(ngo_id)
                st.metric("Assigned Issues", len(issue_ids))
                st.metric("Volunteers", len(volunteers))
        except Exception:
            st.info("Stats not available")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Assigned Issues", "👥 Manage Volunteers", "📨 Applications", "📊 Statistics"])
    
    with tab1:
        render_assigned_issues(ngo_id, username)
    
    with tab2:
        render_manage_volunteers(ngo_id)
    
    with tab3:
        render_volunteer_applications(ngo_id)
    
    with tab4:
        render_statistics(ngo_id)

if __name__ == "__main__":
    main()

