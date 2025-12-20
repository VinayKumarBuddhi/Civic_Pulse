"""
MongoDB Database Connection and Setup
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# MongoDB connection string from environment variable
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'civic_pulse')

# Initialize MongoDB client
@st.cache_resource
def get_mongodb_client():
    """Get MongoDB client connection (cached by Streamlit)"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

def get_database():
    """Get database instance"""
    client = get_mongodb_client()
    if client:
        return client[DATABASE_NAME]
    return None

def get_collection(collection_name: str):
    """Get a specific collection from the database"""
    db = get_database()
    if db:
        return db[collection_name]
    return None

# Collection getters
def get_user_collection():
    return get_collection('User')

def get_reports_collection():
    return get_collection('Reports')

def get_ngo_collection():
    return get_collection('NGO')

def get_volunteers_collection():
    return get_collection('Volunteers')

def get_applications_collection():
    return get_collection('Applications')

def get_admin_collection():
    return get_collection('Admin')

