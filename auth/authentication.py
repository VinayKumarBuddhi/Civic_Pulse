"""
Authentication functions for Civic Pulse
Handles login, registration, and password hashing
"""
import bcrypt
from typing import Tuple, Optional
from database.models import UserModel, NGOModel, VolunteersModel, AdminModel


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password
    
    Args:
        password: Plain text password
        hashed_password: Hashed password string
        
    Returns:
        True if password matches, False otherwise
    """
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def login(username: str, password: str, role: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Authenticate a user based on username, password, and role
    
    Args:
        username: Username to authenticate
        password: Plain text password
        role: User role ('User', 'NGO', 'Volunteer', 'Admin')
        
    Returns:
        Tuple of (success: bool, user_data: dict or None, error_message: str or None)
    """
    user_data = None
    
    try:
        # Find user based on role
        if role == "User":
            user_data = UserModel.find_by_username(username)
        elif role == "NGO":
            user_data = NGOModel.find_by_username(username)
        elif role == "Volunteer":
            user_data = VolunteersModel.find_by_username(username)
        elif role == "Admin":
            user_data = AdminModel.find_by_username(username)
        else:
            return False, None, "Invalid role selected"
        
        # Check if user exists
        if not user_data:
            return False, None, f"User '{username}' not found for role '{role}'"
        
        # Verify password
        stored_password = user_data.get('Password', '')
        if not stored_password or not verify_password(password, stored_password):
            return False, None, "Invalid password"
        
        # Remove password from user data before returning
        user_data.pop('Password', None)
        
        return True, user_data, None
        
    except Exception as e:
        return False, None, f"Authentication error: {str(e)}"


def register_user(name: str, username: str, email: str, phone: str, 
                  address: dict, password: str) -> Tuple[bool, Optional[str]]:
    """
    Register a new user account
    
    Args:
        name: Full name of the user
        username: Unique username
        email: Email address
        phone: Phone number
        address: Address dictionary with area, city, district, state, pincode
        password: Plain text password (will be hashed)
        
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    try:
        # Check if username already exists
        existing_user = UserModel.find_by_username(username)
        if existing_user:
            return False, "Username already exists. Please choose a different username."
        
        # Check if email already exists
        existing_email = UserModel.find_by_email(email)
        if existing_email:
            return False, "Email already registered. Please use a different email."
        
        # Validate required fields
        if not all([name, username, email, phone, password]):
            return False, "All fields are required"
        
        if not address or not all([address.get('area'), address.get('city'), 
                                   address.get('district'), address.get('state'), 
                                   address.get('pincode')]):
            return False, "Complete address information is required"
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Prepare user data
        user_data = {
            "Name": name,
            "Username": username,
            "Email": email,
            "Phone number": phone,
            "Address": address,
            "Password": hashed_password
        }
        
        # Create user
        result = UserModel.create_user(user_data)
        
        if result.inserted_id:
            return True, None
        else:
            return False, "Failed to create user account"
            
    except Exception as e:
        return False, f"Registration error: {str(e)}"

