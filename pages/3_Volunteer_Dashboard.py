"""
Volunteer Dashboard - Civic Pulse
Allows volunteers to view assigned issues, update status, and add progress updates
"""
import streamlit as st
import sys
from pathlib import Path
from bson import ObjectId
from datetime import datetime
import base64
from PIL import Image
import io

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.models import ReportsModel, NGOModel, VolunteersModel
from database.database import get_reports_collection
from auth.session import is_authenticated, get_current_username, get_current_user, require_role, logout_user
from database.schemas import REPORT_STATUS_ENUM

# Page configuration
st.set_page_config(
    page_title="Volunteer Dashboard - Civic Pulse",
    page_icon="👤",
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
    if address_dict.get('district'):
        parts.append(address_dict['district'])
    if address_dict.get('state'):
        parts.append(address_dict['state'])
    if address_dict.get('pincode'):
        parts.append(f"PIN: {address_dict['pincode']}")
    return ", ".join(parts) if parts else "Address not available"

def image_to_base64(image_file):
    """Convert uploaded image to base64 string"""
    try:
        image = Image.open(image_file)
        # Resize if too large (max 800px width)
        if image.width > 800:
            ratio = 800 / image.width
            new_height = int(image.height * ratio)
            image = image.resize((800, new_height), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def update_report_status(report_id: str, status: str):
    """Update report status"""
    try:
        ReportsModel.update_status(report_id, status)
        return True, "Status updated successfully"
    except Exception as e:
        return False, f"Error updating status: {str(e)}"

def update_work_review(report_id: str, review: str):
    """Update work review/comments for a report"""
    try:
        reports_collection = get_reports_collection()
        if reports_collection is None:
            return False, "Database connection error"
        
        reports_collection.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"workReview": review, "updated_at": datetime.now()}}
        )
        return True, "Work review updated successfully"
    except Exception as e:
        return False, f"Error updating work review: {str(e)}"

def update_resolved_image(report_id: str, image_base64: str):
    """Update resolved image for a report"""
    try:
        reports_collection = get_reports_collection()
        if reports_collection is None:
            return False, "Database connection error"
        
        reports_collection.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"resolvedImage": image_base64, "updated_at": datetime.now()}}
        )
        return True, "Resolved image uploaded successfully"
    except Exception as e:
        return False, f"Error uploading image: {str(e)}"

def render_assigned_issues(username):
    """Display issues assigned to this volunteer"""
    st.markdown("### 📋 My Assigned Issues")
    
    try:
        # Get volunteer info
        volunteer = VolunteersModel.find_by_username(username)
        if not volunteer:
            st.error("Volunteer profile not found")
            return
        
        assigned_work_ids = volunteer.get('assignedWorks', [])
        
        if not assigned_work_ids:
            st.info("📭 No issues assigned to you yet. Issues will appear here once your NGO assigns them to you.")
            return
        
        # Fetch all assigned reports
        reports_collection = get_reports_collection()
        if reports_collection is None:
            st.error("Database connection error")
            return
        
        reports = []
        for work_id in assigned_work_ids:
            report = reports_collection.find_one({"_id": ObjectId(work_id)})
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
            reporter_username = report.get('Username', 'Unknown')
            image = report.get('Image', '')
            work_review = report.get('workReview')
            resolved_image = report.get('resolvedImage')
            
            # Format date
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%B %d, %Y at %I:%M %p")
            else:
                date_str = "Date not available"
            
            with st.container():
                st.markdown(f"**Issue ID:** `{report_id[:8]}...` | **Reported by:** {reporter_username}")
                st.markdown(get_status_badge_html(status), unsafe_allow_html=True)
                st.markdown(f"**Reported on:** {date_str}")
                
                st.markdown(f"**Description:** {description}")
                
                if categories:
                    category_tags = " | ".join([f"`{cat}`" for cat in categories])
                    st.markdown(f"**Categories:** {category_tags}")
                
                st.markdown(f"**Location:** {format_address(address)}")
                if location.get('latitude') and location.get('longitude'):
                    st.markdown(f"📍 Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}")
                
                # Display original issue image
                if image:
                    st.markdown("**Original Issue Image:**")
                    try:
                        st.image(image, width=300)
                    except:
                        st.info("Image not available")
                
                st.markdown("---")
                
                # Update Status Section
                with st.expander("🔄 Update Issue Status", expanded=False):
                    current_status_index = REPORT_STATUS_ENUM.index(status) if status in REPORT_STATUS_ENUM else 0
                    new_status = st.selectbox(
                        "Select New Status",
                        REPORT_STATUS_ENUM,
                        index=current_status_index,
                        key=f"status_{report_id}"
                    )
                    if new_status != status:
                        if st.button("Update Status", key=f"update_status_{report_id}"):
                            success, msg = update_report_status(report_id, new_status)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                
                # Add Work Review Section
                with st.expander("📝 Add/Update Work Review", expanded=False):
                    current_review = work_review if work_review else ""
                    review_text = st.text_area(
                        "Work Review/Comments",
                        value=current_review,
                        placeholder="Add your progress update, comments, or review of the work done...",
                        height=100,
                        key=f"review_{report_id}"
                    )
                    if st.button("Save Review", key=f"save_review_{report_id}"):
                        if review_text.strip():
                            success, msg = update_work_review(report_id, review_text.strip())
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.warning("Please enter a review before saving")
                
                # Upload Resolved Image Section
                with st.expander("📸 Upload Resolved Image", expanded=False):
                    if resolved_image:
                        st.markdown("**Current Resolved Image:**")
                        try:
                            st.image(resolved_image, width=300)
                        except:
                            st.info("Current image not available")
                    
                    uploaded_image = st.file_uploader(
                        "Upload Completion/Resolved Image",
                        type=['png', 'jpg', 'jpeg'],
                        help="Upload a photo showing the issue has been resolved",
                        key=f"upload_resolved_{report_id}"
                    )
                    
                    if uploaded_image is not None:
                        if st.button("Upload Image", key=f"upload_image_{report_id}"):
                            image_base64 = image_to_base64(uploaded_image)
                            if image_base64:
                                success, msg = update_resolved_image(report_id, image_base64)
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                # Mark as Resolved Section
                if status != 'resolved':
                    with st.expander("✅ Mark as Resolved", expanded=False):
                        st.markdown("**Mark this issue as completely resolved**")
                        st.info("⚠️ Make sure you have:")
                        st.markdown("1. ✅ Completed all necessary work")
                        st.markdown("2. ✅ Added a work review describing what was done")
                        st.markdown("3. ✅ Uploaded a resolved image (if applicable)")
                        
                        if st.button("Mark as Resolved", key=f"mark_resolved_{report_id}", type="primary"):
                            success, msg = update_report_status(report_id, 'resolved')
                            if success:
                                st.success("✅ Issue marked as resolved!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(msg)
                
                st.markdown("---")
                
    except Exception as e:
        st.error(f"Error fetching issues: {str(e)}")

def main():
    # Check authentication
    if not is_authenticated():
        st.error("❌ You must be logged in to access this page.")
        st.info("Please go to the main page and sign in.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Check role
    if not require_role("Volunteer"):
        current_role = st.session_state.get('user_role', 'Unknown')
        st.error(f"❌ Access denied. This page is for Volunteers only. Your role: {current_role}")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get current volunteer
    username = get_current_username()
    user_data = get_current_user()
    
    if not username:
        st.error("❌ User session error. Please log in again.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get volunteer and NGO info
    try:
        volunteer = VolunteersModel.find_by_username(username)
        if volunteer:
            ngo_id = str(volunteer.get('NGO', ''))
            ngo = NGOModel.find_by_id(ngo_id) if ngo_id else None
            ngo_name = ngo.get('Username', 'Unknown NGO') if ngo else 'Unknown NGO'
        else:
            ngo_name = 'Unknown NGO'
    except:
        ngo_name = 'Unknown NGO'
    
    # Header
    st.title("👤 Volunteer Dashboard")
    st.markdown(f"Welcome, **{username}**!")
    if ngo_name:
        st.markdown(f"**Associated NGO:** {ngo_name}")
    
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
            volunteer = VolunteersModel.find_by_username(username)
            if volunteer:
                assigned_works = volunteer.get('assignedWorks', [])
                # Count resolved issues
                reports_collection = get_reports_collection()
                resolved_count = 0
                if reports_collection is not None:
                    for work_id in assigned_works:
                        report = reports_collection.find_one({"_id": ObjectId(work_id)})
                        if report and report.get('Status') == 'resolved':
                            resolved_count += 1
                st.metric("Total Assigned", len(assigned_works))
                st.metric("Resolved", resolved_count)
        except Exception as e:
            st.info("Stats not available")
    
    # Main content
    render_assigned_issues(username)

if __name__ == "__main__":
    main()

