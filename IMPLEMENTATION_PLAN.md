# Civic Pulse - Implementation Plan

## Project Overview
A civic issue reporting and management system with 4 roles: User, NGO, Volunteer, and Admin. Features include RAG-based chatbot, intelligent NGO-issue mapping, and volunteer management.

## Step-by-Step Implementation Plan

### Phase 1: Project Setup & Database Design

#### Step 1.1: Initialize Project Structure
```
Civic_Pulse/
├── app.py (main Streamlit app)
├── config.py (configuration settings)
├── requirements.txt (dependencies)
├── .env (environment variables)
├── database/
│   ├── models.py (MongoDB schemas/models)
│   ├── database.py (MongoDB connection)
│   └── init_db.py (database initialization)
├── auth/
│   ├── authentication.py (login/logout logic)
│   └── session.py (session management)
├── rag/
│   ├── vector_store.py (vector database setup)
│   ├── embeddings.py (embedding generation)
│   ├── chatbot.py (RAG chatbot implementation)
│   └── ngo_matcher.py (NGO-issue matching using RAG)
├── services/
│   ├── user_service.py (user operations)
│   ├── ngo_service.py (NGO operations)
│   ├── volunteer_service.py (volunteer operations)
│   ├── issue_service.py (issue/report operations)
│   └── admin_service.py (admin operations)
├── pages/
│   ├── 1_User_Dashboard.py
│   ├── 2_NGO_Dashboard.py
│   ├── 3_Volunteer_Dashboard.py
│   ├── 4_Admin_Dashboard.py
│   └── 5_Chatbot.py
└── utils/
    ├── helpers.py (utility functions)
    └── validators.py (input validation)
```

#### Step 1.2: Install Dependencies
```bash
pip install streamlit pymongo python-dotenv bcrypt 
faiss-cpu sentence-transformers langchain openai chromadb pandas 
streamlit-authenticator pillow pybase64
```

#### Step 1.3: Design MongoDB Schema (as per workflow document)

**Collections and Schemas:**

1. **User** Collection:
   - Name
   - Username
   - Address: {area, city, district, state, pincode}
   - Password (hashed)
   - Email
   - Phone number
   - Reported issues: [Reports] (array of report references)

2. **Reports** Collection:
   - ID (ObjectId)
   - Image
   - Description
   - Categories: [] (array)
   - Username (reference to User)
   - Location: {latitude, longitude}
   - Address: {area, city, district, state, pincode}
   - assignedTo: [NGO, volunteers] (array of references)
   - Status: enum('not verified', 'verified', 'assigned', 'in-progress', 'resolved')
   - workReview
   - resolvedImage

3. **NGO** Collection:
   - Username
   - Password (hashed)
   - Categories: [] (array)
   - Location: {latitude, longitude}
   - Address: {area, city, dist, state, pincode}
   - Issues: [Reports] (array of report references)
   - volunteers: [Volunteers] (array of volunteer references)
   - Description
   - Applications (reference to Applications collection)
   - isActive

4. **Volunteers** Collection:
   - Username
   - Password (hashed)
   - NGO (reference to NGO)
   - assignedWorks: [Reports] (array of report references)

5. **Applications** Collection:
   - Username (reference to User)
   - NGOselected (reference to NGO)
   - Description
   - status: enum('pending', 'accepted', 'rejected')

6. **Admin** Collection:
   - Username
   - Password (hashed)

### Phase 2: Authentication & Session Management

#### Step 2.1: Implement Authentication System
- Password hashing with bcrypt
- Session management using Streamlit session state
- Role-based access control decorators
- Login/logout functionality

#### Step 2.2: Create Login Page
- Multi-role login (user, NGO, volunteer, admin)
- Password recovery option
- Session persistence

### Phase 3: User Dashboard & Issue Reporting

#### Step 3.1: User Dashboard Features
- Report new issue (form with: title, description, location, category, images)
- View own reported issues with status
- View assigned NGO for each issue
- Apply as volunteer to NGOs

#### Step 3.2: Issue Reporting Form
- Location picker/map integration
- Category selection
- Image upload (multiple)
- Submit to database

### Phase 4: RAG-Based Chatbot Implementation

#### Step 4.1: Setup Vector Store
- Choose vector DB (FAISS/ChromaDB)
- Initialize embeddings model (Sentence Transformers or OpenAI)
- Create embeddings for:
  - All reported issues (by site/location)
  - NGO information and requirements
  - Site information
  - General FAQ data

#### Step 4.2: Implement RAG Chatbot
- Question processing
- Vector similarity search
- Context retrieval
- Response generation (using LLM like OpenAI or local model)

#### Step 4.3: Chatbot Features
- Query previous reports by site/location
- Get issue status information
- Site information queries
- General queries about civic services
- NGO information queries

### Phase 5: NGO Dashboard & Issue Mapping

#### Step 5.1: RAG-Based NGO-Issue Matching
- When issue is reported, use RAG to:
  - Extract issue requirements/category
  - Match with NGO capabilities/requirements (from vector store)
  - Assign best matching NGO automatically
  - Allow manual override

#### Step 5.2: NGO Dashboard Features
- View assigned issues
- Assign issues to volunteers
- Review volunteer updates
- Manage volunteers (add, remove, assign credentials)
- Update issue status
- View statistics/reports

#### Step 5.3: Volunteer Management (NGO)
- Create volunteer accounts
- Generate username/password for volunteers
- Assign volunteers to issues
- View volunteer activity

### Phase 6: Volunteer Dashboard

#### Step 6.1: Volunteer Features
- View assigned issues
- Update issue status
- Add progress updates/comments
- Upload completion photos
- Mark issues as resolved

### Phase 7: Admin Dashboard

#### Step 7.1: Admin Features
- Manage NGOs (CRUD operations)
- Create NGO accounts with credentials
- Manage volunteers across all NGOs
- View system statistics
- Monitor all issues
- Generate reports

### Phase 8: Integration & Polish

#### Step 8.1: Connect All Components
- Integrate all dashboards
- Connect RAG chatbot to all relevant data sources
- Implement real-time updates

#### Step 8.2: UI/UX Enhancements
- Add Tailwind CSS styling (via streamlit-components)
- Add animations/transitions
- Responsive design
- Loading states
- Error handling

#### Step 8.3: Testing & Deployment
- Test all user flows
- Error handling
- Data validation
- Security checks
- Deploy to Streamlit Cloud or server

## Technical Stack Summary

- **Frontend**: Streamlit
- **Backend**: Python (Streamlit)
- **Database**: MongoDB (using PyMongo)
- **Authentication**: bcrypt, session state
- **RAG/ML**: LangChain, Sentence Transformers, FAISS/ChromaDB
- **Styling**: Streamlit native + custom CSS

## Key Implementation Priorities

1. ✅ Database setup and models
2. ✅ Authentication system
3. ✅ User dashboard and issue reporting
4. ✅ Basic RAG chatbot
5. ✅ NGO dashboard and issue assignment
6. ✅ Volunteer dashboard
7. ✅ Admin dashboard
8. ✅ NGO-issue matching with RAG
9. ✅ Polish and deployment

