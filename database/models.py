"""
MongoDB Models and Helper Functions
Following the exact schema naming conventions from workflow document
"""
from datetime import datetime
from typing import Optional, List, Dict
from bson import ObjectId
from .database import (
    get_user_collection,
    get_reports_collection,
    get_ngo_collection,
    get_volunteers_collection,
    get_applications_collection,
    get_admin_collection
)
from .schemas import (
    REPORT_STATUS_ENUM,
    APPLICATION_STATUS_ENUM
)


class UserModel:
    """User model following workflow document schema"""
    
    @staticmethod
    def create_user(data: Dict):
        """Create a new user"""
        collection = get_user_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot create user.")
        user_data = {
            "Name": data.get("Name"),
            "Username": data.get("Username"),
            "Address": data.get("Address"),
            "Password": data.get("Password"),  # Should be hashed before calling
            "Email": data.get("Email"),
            "Phone number": data.get("Phone number"),
            "Reported issues": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(user_data)
    
    @staticmethod
    def find_by_username(username: str):
        """Find user by username"""
        collection = get_user_collection()
        return collection.find_one({"Username": username})
    
    @staticmethod
    def find_by_email(email: str):
        """Find user by email"""
        collection = get_user_collection()
        return collection.find_one({"Email": email})


class ReportsModel:
    """Reports model following workflow document schema"""
    
    @staticmethod
    def create_report(data: Dict):
        """Create a new report"""
        collection = get_reports_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot create report.")
        report_data = {
            "Image": data.get("Image", ""),
            "Description": data.get("Description"),
            "Categories": data.get("Categories", []),
            "Username": data.get("Username"),
            "Location": data.get("Location"),
            "Address": data.get("Address"),
            "assignedTo": [],
            "Status": "not verified",  # Default status
            "workReview": None,
            "resolvedImage": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(report_data)
    
    @staticmethod
    def find_by_id(report_id: str):
        """Find report by ID"""
        collection = get_reports_collection()
        return collection.find_one({"_id": ObjectId(report_id)})
    
    @staticmethod
    def find_by_username(username: str):
        """Find reports by username"""
        collection = get_reports_collection()
        return list(collection.find({"Username": username}))
    
    @staticmethod
    def update_status(report_id: str, status: str):
        """Update report status"""
        if status not in REPORT_STATUS_ENUM:
            raise ValueError(f"Invalid status. Must be one of {REPORT_STATUS_ENUM}")
        collection = get_reports_collection()
        return collection.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"Status": status, "updated_at": datetime.now()}}
        )


class NGOModel:
    """NGO model following workflow document schema"""
    
    @staticmethod
    def create_ngo(data: Dict):
        """Create a new NGO"""
        collection = get_ngo_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot create NGO.")
        ngo_data = {
            "Username": data.get("Username"),
            "Password": data.get("Password"),  # Should be hashed before calling
            "Categories": data.get("Categories", []),
            "Location": data.get("Location"),
            "Address": data.get("Address"),
            "Issues": [],
            "volunteers": [],
            "Description": data.get("Description", ""),
            "Applications": [],
            "isActive": data.get("isActive", True),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(ngo_data)
    
    @staticmethod
    def find_by_username(username: str):
        """Find NGO by username"""
        collection = get_ngo_collection()
        return collection.find_one({"Username": username})
    
    @staticmethod
    def find_by_id(ngo_id: str):
        """Find NGO by ID"""
        collection = get_ngo_collection()
        return collection.find_one({"_id": ObjectId(ngo_id)})
    
    @staticmethod
    def find_all_active():
        """Find all active NGOs"""
        collection = get_ngo_collection()
        return list(collection.find({"isActive": True}))
    
    @staticmethod
    def find_all():
        """Find all NGOs"""
        collection = get_ngo_collection()
        return list(collection.find({}))
    



class VolunteersModel:
    """Volunteers model following workflow document schema"""
    
    @staticmethod
    def create_volunteer(data: Dict):
        """Create a new volunteer"""
        collection = get_volunteers_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot create volunteer.")
        volunteer_data = {
            "Username": data.get("Username"),
            "Password": data.get("Password"),  # Should be hashed before calling
            "NGO": ObjectId(data.get("NGO")),
            "assignedWorks": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(volunteer_data)
    
    @staticmethod
    def find_by_username(username: str):
        """Find volunteer by username"""
        collection = get_volunteers_collection()
        return collection.find_one({"Username": username})
    
    @staticmethod
    def find_by_ngo(ngo_id: str):
        """Find volunteers by NGO"""
        collection = get_volunteers_collection()
        return list(collection.find({"NGO": ObjectId(ngo_id)}))
    
    @staticmethod
    def delete_volunteer(volunteer_id: str):
        """Delete a volunteer"""
        collection = get_volunteers_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot delete volunteer.")
        return collection.delete_one({"_id": ObjectId(volunteer_id)})


class ApplicationsModel:
    """Applications model following workflow document schema"""
    
    @staticmethod
    def create_application(data: Dict):
        """Create a new application"""
        collection = get_applications_collection()
        if collection is None:
            raise ConnectionError("Database connection failed. Cannot create application.")
        application_data = {
            "Username": data.get("Username"),
            "NGOselected": ObjectId(data.get("NGOselected")),
            "Description": data.get("Description", ""),
            "status": "pending",  # Default status
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(application_data)
    
    @staticmethod
    def update_status(application_id: str, status: str):
        """Update application status"""
        if status not in APPLICATION_STATUS_ENUM:
            raise ValueError(f"Invalid status. Must be one of {APPLICATION_STATUS_ENUM}")
        collection = get_applications_collection()
        return collection.update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
    
    @staticmethod
    def find_by_ngo(ngo_id: str):
        """Find applications by NGO"""
        collection = get_applications_collection()
        return list(collection.find({"NGOselected": ObjectId(ngo_id)}))
    
    @staticmethod
    def find_by_username_and_ngo(username: str, ngo_id: str):
        """Find application by username and NGO"""
        collection = get_applications_collection()
        if collection is None:
            return None
        return collection.find_one({"Username": username, "NGOselected": ObjectId(ngo_id)})


class AdminModel:
    """Admin model following workflow document schema"""
    
    @staticmethod
    def create_admin(data: Dict):
        """Create a new admin"""
        collection = get_admin_collection()
        admin_data = {
            "Username": data.get("Username"),
            "Password": data.get("Password"),  # Should be hashed before calling
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return collection.insert_one(admin_data)
    
    @staticmethod
    def find_by_username(username: str):
        """Find admin by username"""
        collection = get_admin_collection()
        return collection.find_one({"Username": username})

