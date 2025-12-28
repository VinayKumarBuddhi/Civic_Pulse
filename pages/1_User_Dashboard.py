"""
User Dashboard - Civic Pulse
Allows users to report issues, view their reports, and apply as volunteers to NGOs
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

from database.models import ReportsModel, NGOModel, ApplicationsModel, UserModel
from database.database import get_reports_collection
from auth.session import is_authenticated, get_current_username, get_current_user, require_role, logout_user
from database.schemas import REPORT_STATUS_ENUM, APPLICATION_STATUS_ENUM

# Page configuration
st.set_page_config(
    page_title="User Dashboard - Civic Pulse",
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
        .status-not-verified {
            background-color: #ffebee;
            color: #c62828;
        }
        .status-verified {
            background-color: #fff3e0;
            color: #e65100;
        }
        .status-assigned {
            background-color: #e3f2fd;
            color: #1565c0;
        }
        .status-in-progress {
            background-color: #f3e5f5;
            color: #6a1b9a;
        }
        .status-resolved {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        .issue-card {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            background-color: #f9f9f9;
        }
    </style>
""", unsafe_allow_html=True)

# Common issue categories
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

def get_status_badge_html(status):
    """Get HTML for status badge"""
    status_class = f"status-{status.replace(' ', '-').replace('-', '-')}"
    status_class = status_class.replace('--', '-')
    status_class = status_class.replace('in-progress', 'in-progress')
    if 'not verified' in status:
        status_class = "status-not-verified"
    elif status == 'verified':
        status_class = "status-verified"
    elif status == 'assigned':
        status_class = "status-assigned"
    elif status == 'in-progress':
        status_class = "status-in-progress"
    elif status == 'resolved':
        status_class = "status-resolved"
    
    return f'<span class="status-badge {status_class}">{status.upper()}</span>'

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

def render_report_issue_form(username):
    """Render form to report a new issue"""
    st.markdown("### 📝 Report New Issue")
    
    with st.form("report_issue_form", clear_on_submit=True):
        # Description
        description = st.text_area("Issue Description *", placeholder="Describe the issue in detail...", height=150)
        
        # Categories (multi-select)
        categories = st.multiselect("Categories *", ISSUE_CATEGORIES, help="Select one or more categories that best describe the issue")
        
        # Location (Latitude and Longitude)
        st.markdown("**Location (GPS Coordinates)**")
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input("Latitude *", min_value=-90.0, max_value=90.0, value=0.0, step=0.000001, format="%.6f")
        with col2:
            longitude = st.number_input("Longitude *", min_value=-180.0, max_value=180.0, value=0.0, step=0.000001, format="%.6f")
        
        st.info("💡 Tip: You can get coordinates from Google Maps by right-clicking on a location")
        
        # Address
        st.markdown("**Address**")
        col1, col2 = st.columns(2)
        with col1:
            area = st.text_input("Area/Locality *", placeholder="Area or Locality")
            city = st.text_input("City *", placeholder="City")
            district = st.text_input("District *", placeholder="District")
        with col2:
            state = st.text_input("State *", placeholder="State")
            pincode = st.text_input("Pincode *", placeholder="PIN Code")
        
        # Image upload
        uploaded_image = st.file_uploader("Upload Image (Optional)", type=['png', 'jpg', 'jpeg'], help="Upload a photo of the issue")
        
        submitted = st.form_submit_button("Submit Issue Report", use_container_width=True, type="primary")
        
        if submitted:
            # Validation
            if not description:
                st.error("Please provide an issue description")
            elif not categories:
                st.error("Please select at least one category")
            elif latitude == 0.0 and longitude == 0.0:
                st.error("Please provide valid GPS coordinates")
            elif not all([area, city, district, state, pincode]):
                st.error("Please fill in all address fields")
            else:
                try:
                    # Prepare report data
                    report_data = {
                        "Username": username,
                        "Description": description,
                        "Categories": categories,
                        "Location": {
                            "latitude": float(latitude),
                            "longitude": float(longitude)
                        },
                        "Address": {
                            "area": area,
                            "city": city,
                            "district": district,
                            "state": state,
                            "pincode": pincode
                        },
                        "Image": ""
                    }
                    
                    # Process image if uploaded
                    if uploaded_image is not None:
                        image_base64 = image_to_base64(uploaded_image)
                        if image_base64:
                            report_data["Image"] = image_base64
                    
                    # Create report
                    result = ReportsModel.create_report(report_data)
                    
                    if result.inserted_id:
                        report_id = str(result.inserted_id)
                        
                        # Step 3: Verify issue and calculate severity (async or background)
                        # Import here to avoid circular imports
                        try:
                            from services.issue_verifier import verify_and_score_issue
                            
                            # Verify issue and calculate severity
                            with st.spinner("🔍 Verifying issue and calculating severity..."):
                                verification_result = verify_and_score_issue(
                                    report_data.get("Image", ""),
                                    description,
                                    categories
                                )
                                
                                if verification_result['is_valid']:
                                    # Update report with verification status and severity score
                                    ReportsModel.update_status_and_severity(
                                        report_id,
                                        'verified',
                                        verification_result['severity_score']
                                    )
                                    st.success(f"✅ Issue verified! Severity Score: {verification_result['severity_score']}/10.0")
                                    st.success("✅ Issue reported successfully! It will be assigned to an appropriate NGO.")
                                    st.balloons()
                                else:
                                    # Keep status as "not verified"
                                    st.warning(f"⚠️ Issue verification inconclusive (confidence: {verification_result['confidence']:.2f}). Report submitted for manual review.")
                        except ImportError:
                            # If verification module not available, just create the report
                            st.success("✅ Issue reported successfully! It will be reviewed and assigned to an appropriate NGO.")
                            st.info("ℹ️ Issue verification module not available. Please install TensorFlow for automatic verification.")
                        except Exception as e:
                            # If verification fails, still save the report
                            st.success("✅ Issue reported successfully! It will be reviewed and assigned to an appropriate NGO.")
                            st.warning(f"⚠️ Automatic verification failed: {str(e)}. Report submitted for manual review.")
                    else:
                        st.error("Failed to create issue report. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error creating report: {str(e)}")

def render_my_reports(username):
    """Display user's reported issues"""
    st.markdown("### 📋 My Reported Issues")
    
    try:
        reports = ReportsModel.find_by_username(username)
        
        if not reports:
            st.info("📭 You haven't reported any issues yet. Use the form above to report your first issue!")
            return
        
        # Sort by creation date (newest first)
        reports.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        st.markdown(f"**Total Issues Reported: {len(reports)}**")
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
            image = report.get('Image', '')
            work_review = report.get('workReview')
            resolved_image = report.get('resolvedImage')
            
            # Format created date
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%B %d, %Y at %I:%M %p")
            else:
                date_str = "Date not available"
            
            # Display report card
            with st.container():
                st.markdown(f"**Issue ID:** `{report_id[:8]}...`")
                st.markdown(get_status_badge_html(status), unsafe_allow_html=True)
                st.markdown(f"**Reported on:** {date_str}")
                
                st.markdown(f"**Description:** {description}")
                
                if categories:
                    category_tags = " | ".join([f"`{cat}`" for cat in categories])
                    st.markdown(f"**Categories:** {category_tags}")
                
                st.markdown(f"**Location:** {format_address(address)}")
                if location.get('latitude') and location.get('longitude'):
                    st.markdown(f"📍 Coordinates: {location['latitude']:.6f}, {location['longitude']:.6f}")
                
                # Show assigned NGO if any
                if assigned_to:
                    st.markdown("**Assigned To:**")
                    for assigned in assigned_to:
                        if isinstance(assigned, ObjectId):
                            try:
                                ngo = NGOModel.find_by_id(str(assigned))
                                if ngo:
                                    st.markdown(f"  - 🏢 {ngo.get('Username', 'Unknown NGO')}")
                            except:
                                pass
                
                # Show work review if available
                if work_review:
                    st.markdown(f"**Work Review:** {work_review}")
                
                # Display images
                col1, col2 = st.columns(2)
                with col1:
                    if image:
                        st.markdown("**Original Image:**")
                        try:
                            # Display base64 image
                            st.image(image, width=300)
                        except:
                            st.info("Image not available")
                
                with col2:
                    if resolved_image:
                        st.markdown("**Resolved Image:**")
                        try:
                            st.image(resolved_image, width=300)
                        except:
                            st.info("Resolved image not available")
                
                st.markdown("---")
                
    except Exception as e:
        st.error(f"Error fetching reports: {str(e)}")

def render_volunteer_application(username):
    """Render form to apply as volunteer to NGOs"""
    st.markdown("### 🤝 Apply as Volunteer to NGOs")
    
    try:
        # Get all active NGOs
        ngos = NGOModel.find_all_active()
        
        if not ngos:
            st.info("📭 No active NGOs available at the moment.")
            return
        
        st.markdown("Select an NGO you'd like to volunteer with:")
        
        # Create NGO selection dropdown
        ngo_options = {f"{ngo.get('Username', 'Unknown')} - {format_address(ngo.get('Address', {}))}": str(ngo.get('_id', '')) 
                       for ngo in ngos}
        
        selected_ngo_display = st.selectbox("Select NGO *", list(ngo_options.keys()))
        selected_ngo_id = ngo_options.get(selected_ngo_display, '')
        
        # Show NGO details
        if selected_ngo_id:
            ngo = NGOModel.find_by_id(selected_ngo_id)
            if ngo:
                with st.expander("View NGO Details"):
                    st.markdown(f"**Description:** {ngo.get('Description', 'No description available')}")
                    categories = ngo.get('Categories', [])
                    if categories:
                        st.markdown(f"**Categories:** {', '.join(categories)}")
                    st.markdown(f"**Location:** {format_address(ngo.get('Address', {}))}")
        
        # Application description
        description = st.text_area("Why do you want to volunteer with this NGO? *", 
                                   placeholder="Tell us about your motivation and relevant experience...", 
                                   height=100)
        
        # Check if user already applied
        if selected_ngo_id:
            try:
                # Get all applications for this NGO by this user
                all_applications = ApplicationsModel.find_by_ngo(selected_ngo_id)
                user_applications = [app for app in all_applications if app.get('Username') == username]
                
                if user_applications:
                    existing_app = user_applications[0]
                    existing_status = existing_app.get('status', 'pending')
                    st.warning(f"⚠️ You have already applied to this NGO. Status: **{existing_status.upper()}**")
                    if existing_status == 'pending':
                        st.info("Your application is still pending review. Please wait for the NGO to respond.")
                        return
            except:
                pass
        
        # Submit application
        if st.button("Submit Application", use_container_width=True, type="primary"):
            if not selected_ngo_id:
                st.error("Please select an NGO")
            elif not description:
                st.error("Please provide a description")
            else:
                try:
                    application_data = {
                        "Username": username,
                        "NGOselected": selected_ngo_id,
                        "Description": description
                    }
                    
                    result = ApplicationsModel.create_application(application_data)
                    
                    if result.inserted_id:
                        st.success("✅ Application submitted successfully! The NGO will review your application.")
                        st.balloons()
                    else:
                        st.error("Failed to submit application. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error submitting application: {str(e)}")
                    
    except Exception as e:
        st.error(f"Error loading NGOs: {str(e)}")

# Main dashboard
def main():
    # Check authentication
    if not is_authenticated():
        st.error("❌ You must be logged in to access this page.")
        st.info("Please go to the main page and sign in.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Check role
    if not require_role("User"):
        current_role = st.session_state.get('user_role', 'Unknown')
        st.error(f"❌ Access denied. This page is for Users only. Your role: {current_role}")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Get current user
    username = get_current_username()
    user_data = get_current_user()
    
    if not username:
        st.error("❌ User session error. Please log in again.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
        return
    
    # Header
    st.title("👤 User Dashboard")
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
            reports = ReportsModel.find_by_username(username)
            total_reports = len(reports)
            resolved_reports = len([r for r in reports if r.get('Status') == 'resolved'])
            st.metric("Total Issues", total_reports)
            st.metric("Resolved Issues", resolved_reports)
        except:
            st.info("Stats not available")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📝 Report Issue", "📋 My Reports", "🤝 Apply as Volunteer"])
    
    with tab1:
        render_report_issue_form(username)
    
    with tab2:
        render_my_reports(username)
    
    with tab3:
        render_volunteer_application(username)

if __name__ == "__main__":
    main()

