"""
MongoDB Schemas for Civic Pulse Application
Based on the workflow document specifications
"""

from pymongo import MongoClient
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId

# Schema Definitions (Python dictionaries representing MongoDB documents)

# 1. User Schema
USER_SCHEMA = {
    "Name": str,
    "Username": str,  # Unique
    "Address": {
        "area": str,
        "city": str,
        "district": str,
        "state": str,
        "pincode": str
    },
    "Password": str,  # Will be hashed using bcrypt
    "Email": str,  # Unique
    "Phone number": str,
    "Reported issues": list,  # Array of Report ObjectIds or references
    "created_at": datetime,
    "updated_at": datetime
}

# 2. Reports Schema
REPORTS_SCHEMA = {
    "_id": ObjectId,  # Auto-generated ID
    "Image": str,  # Base64 encoded or file path
    "Description": str,
    "Categories": list,  # Array of category strings
    "Username": str,  # Reference to User.Username
    "Location": {
        "latitude": float,
        "longitude": float
    },
    "Address": {
        "area": str,
        "city": str,
        "district": str,
        "state": str,
        "pincode": str
    },
    "assignedTo": list,  # Array of [NGO, volunteers] references
    "Status": str,  # enum: 'not verified', 'verified', 'assigned', 'in-progress', 'resolved'
    "workReview": Optional[str],
    "resolvedImage": Optional[str],  # Base64 encoded or file path
    "created_at": datetime,
    "updated_at": datetime
}

# 3. NGO Schema
NGO_SCHEMA = {
    "Username": str,  # Unique
    "Password": str,  # Will be hashed using bcrypt
    "Categories": list,  # Array of category strings
    "Location": {
        "latitude": float,
        "longitude": float
    },
    "Address": {
        "area": str,
        "city": str,
        "dist": str,  # Note: workflow doc uses "dist" not "district"
        "state": str,
        "pincode": str
    },
    "Issues": list,  # Array of Report ObjectIds or references
    "volunteers": list,  # Array of Volunteer ObjectIds or references
    "Description": str,
    "Applications": list,  # Array of Application ObjectIds or references
    "isActive": bool,
    "created_at": datetime,
    "updated_at": datetime
}

# 4. Volunteers Schema
VOLUNTEERS_SCHEMA = {
    "Username": str,  # Unique
    "Password": str,  # Will be hashed using bcrypt
    "NGO": ObjectId,  # Reference to NGO _id
    "assignedWorks": list,  # Array of Report ObjectIds or references
    "created_at": datetime,
    "updated_at": datetime
}

# 5. Applications Schema
APPLICATIONS_SCHEMA = {
    "Username": str,  # Reference to User.Username
    "NGOselected": ObjectId,  # Reference to NGO _id
    "Description": str,
    "status": str,  # enum: 'pending', 'accepted', 'rejected'
    "created_at": datetime,
    "updated_at": datetime
}

# 6. Admin Schema
ADMIN_SCHEMA = {
    "Username": str,  # Unique
    "Password": str,  # Will be hashed using bcrypt
    "created_at": datetime,
    "updated_at": datetime
}

# Status Enums
REPORT_STATUS_ENUM = ['not verified', 'verified', 'assigned', 'in-progress', 'resolved']
APPLICATION_STATUS_ENUM = ['pending', 'accepted', 'rejected']

# Collection Names (exact as per workflow document)
COLLECTIONS = {
    'User': 'User',
    'Reports': 'Reports',
    'NGO': 'NGO',
    'Volunteers': 'Volunteers',
    'Applications': 'Applications',
    'Admin': 'Admin'
}

