# Civic Pulse - Step-by-Step Build Guide

## Prerequisites Setup

### Step 1: Environment Setup
1. Create virtual environment
2. Install all dependencies from `requirements.txt`
3. Set up MongoDB (local or cloud like MongoDB Atlas)
4. Create `.env` file with MongoDB connection string
5. Test MongoDB connection

---

## Phase 1: Database Foundation

### Step 2: Database Connection
1. Implement MongoDB connection in `database/database.py`
2. Test database connectivity
3. Verify database and collections are accessible

### Step 3: Database Models/Helpers
1. Complete all model classes in `database/models.py`
2. Add helper methods for common operations (create, read, update, delete)
3. Add validation functions for each model
4. Test each model's CRUD operations

---

## Phase 2: Authentication System

### Step 4: Authentication Module
1. Create `auth/authentication.py` with login/logout functions
2. Implement password hashing with bcrypt
3. Create session management in `auth/session.py` using Streamlit session state
4. Create role-based access control decorators/helpers
5. Test authentication for all roles (User, NGO, Volunteer, Admin)

### Step 5: Login Page
1. Create main login page in `app.py`
2. Design login form with role selection
3. Integrate authentication with database
4. Add error handling and validation
5. Implement session persistence

### Step 6: Registration (User Only)
1. Create user registration form
2. Validate input fields
3. Hash password before storing
4. Store user data in MongoDB User collection
5. Redirect to login after successful registration

---

## Phase 3: User Dashboard & Issue Reporting

### Step 7: User Dashboard Structure
1. Create `pages/1_User_Dashboard.py`
2. Add navigation and layout
3. Implement role check (ensure only users can access)

### Step 8: Issue Reporting Form
1. Create form to report new issues
2. Add fields: Description, Categories (multi-select), Location (latitude/longitude), Address (area, city, district, state, pincode)
3. Add image upload functionality
4. Store image as base64 or file path
5. Save report to Reports collection with status "not verified"
6. Update User's "Reported issues" array with new report ID

### Step 9: View Own Reports
1. Fetch user's reports from database
2. Display reports in a table/cards with status
3. Show assigned NGO if available
4. Add filters (by status, date, category)

---

## Phase 4: RAG System Setup

### Step 10: Vector Store Setup
1. Create `rag/vector_store.py`
2. Choose vector database (FAISS or ChromaDB)
3. Initialize embeddings model (Sentence Transformers)
4. Create function to initialize/load vector store

### Step 11: Embeddings Generation
1. Create `rag/embeddings.py`
2. Implement function to generate embeddings for documents
3. Create embeddings for:
   - All Reports (description + location + categories)
   - NGO information (description + categories + location)
   - Site/location information
4. Store embeddings in vector database

### Step 12: RAG Chatbot Implementation
1. Create `rag/chatbot.py`
2. Implement question processing
3. Implement vector similarity search
4. Implement context retrieval from top matches
5. Integrate LLM (OpenAI API or local model) for response generation
6. Store chat history in database (optional: create ChatHistory collection)

### Step 13: Chatbot UI
1. Create `pages/5_Chatbot.py`
2. Design chat interface
3. Connect to RAG chatbot backend
4. Display chat history
5. Handle user queries and display responses

---

## Phase 5: NGO Dashboard

### Step 14: NGO-Issue Matching (RAG-Based)
1. Create `rag/ngo_matcher.py`
2. When new report is created, extract issue requirements/categories
3. Match with NGO capabilities (Categories, Description, Location) using vector similarity
4. Assign best matching NGO to report
5. Update Reports.assignedTo and NGO.Issues arrays

### Step 15: NGO Dashboard Structure
1. Create `pages/2_NGO_Dashboard.py`
2. Add navigation and layout
3. Implement role check (ensure only NGOs can access)

### Step 16: View Assigned Issues
1. Fetch NGO's assigned issues from NGO.Issues array
2. Display issues with details and status
3. Add filters and search functionality

### Step 17: Assign Issues to Volunteers
1. Fetch NGO's volunteers list
2. Create interface to assign issue to volunteer(s)
3. Update Reports.assignedTo array
4. Update Volunteers.assignedWorks array

### Step 18: Volunteer Management (NGO)
1. Create form to add new volunteers
2. Generate username and password for volunteers
3. Hash password and store in Volunteers collection
4. Update NGO.volunteers array
5. Display list of NGO's volunteers

### Step 19: Review Reports
1. Allow NGO to review volunteer updates (workReview field)
2. Update report status if needed
3. View resolved images

---

## Phase 6: Volunteer Dashboard

### Step 20: Volunteer Dashboard Structure
1. Create `pages/3_Volunteer_Dashboard.py`
2. Add navigation and layout
3. Implement role check (ensure only volunteers can access)

### Step 21: View Assigned Works
1. Fetch volunteer's assigned works from Volunteers.assignedWorks array
2. Display assigned reports with details
3. Show current status

### Step 22: Update Issue Status
1. Create interface to update report status
2. Allow status transitions: 'assigned' → 'in-progress' → 'resolved'
3. Add workReview text field
4. Upload resolvedImage when marking as resolved
5. Update Reports collection with new status, workReview, and resolvedImage

---

## Phase 7: Applications System

### Step 23: User Application to NGO
1. Add "Apply as Volunteer" feature in User Dashboard
2. List all active NGOs
3. Create application form (select NGO, add description)
4. Save to Applications collection with status "pending"
5. Update User's applications (if needed)

### Step 24: NGO View Applications
1. Display applications in NGO Dashboard
2. Show application details and user information
3. Allow NGO to accept or reject applications
4. Update Applications.status field
5. If accepted, create Volunteer account and update NGO.volunteers

---

## Phase 8: Admin Dashboard

### Step 25: Admin Dashboard Structure
1. Create `pages/4_Admin_Dashboard.py`
2. Add navigation and layout
3. Implement role check (ensure only admins can access)

### Step 26: Manage NGOs
1. Create form to add new NGOs
2. Generate username and password for NGOs
3. Store NGO data in NGO collection
4. Display list of all NGOs
5. Edit/Update NGO information
6. Activate/Deactivate NGOs (update isActive field)

### Step 27: Manage Volunteers
1. Display all volunteers across all NGOs
2. View volunteer assignments
3. Edit/Update volunteer information
4. Remove volunteers if needed

### Step 28: System Statistics
1. Display total users, NGOs, volunteers, reports
2. Show reports by status (pie chart/bar chart)
3. Show reports by category
4. Display active vs inactive NGOs
5. Show recent activities/logs

---

## Phase 9: Integration & Enhancements

### Step 29: Connect All Components
1. Ensure all dashboards are accessible from main app
2. Test complete user flows:
   - User reports issue → NGO gets assigned → Volunteer updates → Status changes
   - User applies to NGO → NGO accepts → Volunteer account created
3. Fix any integration issues

### Step 30: RAG Chatbot Integration
1. Connect chatbot to all relevant data:
   - Query reports by location/site
   - Get NGO information
   - Get issue status
   - General civic service queries
2. Test various query types
3. Improve response quality

### Step 31: UI/UX Enhancements
1. Add Tailwind CSS styling or custom CSS
2. Add animations and transitions
3. Improve form layouts and validation messages
4. Add loading states
5. Add success/error notifications
6. Make responsive design

### Step 32: Error Handling & Validation
1. Add comprehensive error handling throughout
2. Add input validation for all forms
3. Add proper error messages
4. Handle edge cases

---

## Phase 10: Testing & Deployment

### Step 33: Testing
1. Test all user roles and permissions
2. Test all CRUD operations
3. Test RAG chatbot with various queries
4. Test NGO-issue matching accuracy
5. Test image uploads
6. Test session management

### Step 34: Security Checks
1. Ensure all passwords are hashed
2. Verify role-based access is working
3. Check for SQL injection (MongoDB injection) vulnerabilities
4. Validate all inputs
5. Secure API keys in .env file

### Step 35: Deployment
1. Prepare deployment files
2. Set up MongoDB Atlas or production MongoDB
3. Deploy to Streamlit Cloud or server
4. Configure environment variables
5. Test deployed application

---

## Summary of Key Files to Create

### Core Files
- `app.py` - Main Streamlit app with routing
- `config.py` - Configuration settings
- `.env` - Environment variables

### Database (Already Created)
- `database/database.py` - MongoDB connection
- `database/models.py` - Model classes
- `database/schemas.py` - Schema definitions

### Authentication
- `auth/authentication.py` - Login/logout logic
- `auth/session.py` - Session management

### RAG System
- `rag/vector_store.py` - Vector database setup
- `rag/embeddings.py` - Embedding generation
- `rag/chatbot.py` - RAG chatbot
- `rag/ngo_matcher.py` - NGO-issue matching

### Services (Optional - for business logic)
- `services/user_service.py`
- `services/ngo_service.py`
- `services/volunteer_service.py`
- `services/issue_service.py`
- `services/admin_service.py`

### Pages
- `pages/1_User_Dashboard.py`
- `pages/2_NGO_Dashboard.py`
- `pages/3_Volunteer_Dashboard.py`
- `pages/4_Admin_Dashboard.py`
- `pages/5_Chatbot.py`

### Utils
- `utils/helpers.py` - Utility functions
- `utils/validators.py` - Input validation

---

## Build Order Recommendation

**Week 1: Foundation**
- Steps 1-6 (Environment, Database, Authentication)

**Week 2: Core Features**
- Steps 7-9 (User Dashboard & Issue Reporting)
- Steps 10-13 (RAG System Setup)

**Week 3: Advanced Features**
- Steps 14-19 (NGO Dashboard & Matching)
- Steps 20-22 (Volunteer Dashboard)

**Week 4: Completion**
- Steps 23-28 (Applications & Admin)
- Steps 29-35 (Integration, Testing, Deployment)

