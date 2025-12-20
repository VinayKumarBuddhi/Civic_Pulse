"""
Database Initialization Script
Creates indexes for better performance and enforces unique constraints
Note: Collections are created automatically on first insert, but indexes should be created explicitly
"""
from .database import (
    get_user_collection,
    get_reports_collection,
    get_ngo_collection,
    get_volunteers_collection,
    get_applications_collection,
    get_admin_collection
)
from pymongo.errors import OperationFailure


def create_indexes():
    """
    Create indexes on collections for better performance and unique constraints.
    This is optional but recommended for production.
    
    Note: Collections are created automatically on first document insert.
    This function only creates indexes - it doesn't create collections.
    """
    
    try:
        # User Collection Indexes
        user_collection = get_user_collection()
        if user_collection is not None:
            # Unique index on Username
            user_collection.create_index("Username", unique=True)
            # Unique index on Email
            user_collection.create_index("Email", unique=True)
            print("✅ User collection indexes created")
        
        # NGO Collection Indexes
        ngo_collection = get_ngo_collection()
        if ngo_collection is not None:
            # Unique index on Username
            ngo_collection.create_index("Username", unique=True)
            print("✅ NGO collection indexes created")
        
        # Volunteers Collection Indexes
        volunteers_collection = get_volunteers_collection()
        if volunteers_collection is not None:
            # Unique index on Username
            volunteers_collection.create_index("Username", unique=True)
            # Index on NGO for faster queries
            volunteers_collection.create_index("NGO")
            print("✅ Volunteers collection indexes created")
        
        # Reports Collection Indexes
        reports_collection = get_reports_collection()
        if reports_collection is not None:
            # Index on Username for faster queries
            reports_collection.create_index("Username")
            # Index on Status for filtering
            reports_collection.create_index("Status")
            # Index on Location for geospatial queries (if needed later)
            # reports_collection.create_index([("Location.latitude", 1), ("Location.longitude", 1)])
            print("✅ Reports collection indexes created")
        
        # Applications Collection Indexes
        applications_collection = get_applications_collection()
        if applications_collection is not None:
            # Index on NGOselected for faster queries
            applications_collection.create_index("NGOselected")
            # Index on Username
            applications_collection.create_index("Username")
            print("✅ Applications collection indexes created")
        
        # Admin Collection Indexes
        admin_collection = get_admin_collection()
        if admin_collection is not None:
            # Unique index on Username
            admin_collection.create_index("Username", unique=True)
            print("✅ Admin collection indexes created")
        
        print("\n🎉 All indexes created successfully!")
        return True
        
    except OperationFailure as e:
        print(f"⚠️ Warning: Some indexes may already exist: {e}")
        return False
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False


def verify_connection():
    """Verify MongoDB connection"""
    from .database import get_database
    
    db = get_database()
    if db is None:
        print("❌ Failed to connect to MongoDB")
        return False
    
    # Test connection
    try:
        db.command('ping')
        print("✅ MongoDB connection successful!")
        print(f"✅ Database: {db.name}")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False


if __name__ == "__main__":
    """Run this script to initialize database indexes"""
    print("=" * 50)
    print("MongoDB Database Initialization")
    print("=" * 50)
    print("\nNote: Collections are created automatically on first insert.")
    print("This script only creates indexes for better performance.\n")
    
    # Verify connection
    if verify_connection():
        print("\n" + "=" * 50)
        print("Creating Indexes...")
        print("=" * 50 + "\n")
        create_indexes()
    else:
        print("\n❌ Cannot proceed without database connection.")
        print("Please check your MongoDB connection string in .env file")

