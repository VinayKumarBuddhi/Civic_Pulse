"""
Session management for Civic Pulse
Uses Streamlit session state to manage user authentication
"""
import streamlit as st


def login_user(user_data: dict, role: str):
    """
    Set session state after successful login
    
    Args:
        user_data: User data dictionary (without password)
        role: User role ('User', 'NGO', 'Volunteer', 'Admin')
    """
    st.session_state.authenticated = True
    st.session_state.user_role = role
    st.session_state.username = user_data.get('Username', '')
    st.session_state.user_data = user_data
    st.session_state.user_id = str(user_data.get('_id', ''))


def logout_user():
    """Clear session state and log out user"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.user_data = None
    st.session_state.user_id = None


def is_authenticated() -> bool:
    """
    Check if user is currently authenticated
    
    Returns:
        True if user is logged in, False otherwise
    """
    return st.session_state.get('authenticated', False)


def get_current_user() -> dict | None:
    """
    Get current user data from session
    
    Returns:
        User data dictionary or None if not authenticated
    """
    if is_authenticated():
        return st.session_state.get('user_data', None)
    return None


def get_current_role() -> str | None:
    """
    Get current user role from session
    
    Returns:
        User role string or None if not authenticated
    """
    if is_authenticated():
        return st.session_state.get('user_role', None)
    return None


def get_current_username() -> str | None:
    """
    Get current username from session
    
    Returns:
        Username string or None if not authenticated
    """
    if is_authenticated():
        return st.session_state.get('username', None)
    return None


def require_role(required_role: str) -> bool:
    """
    Check if current user has the required role
    
    Args:
        required_role: Required role to check
        
    Returns:
        True if user has required role, False otherwise
    """
    if not is_authenticated():
        return False
    return st.session_state.get('user_role') == required_role

