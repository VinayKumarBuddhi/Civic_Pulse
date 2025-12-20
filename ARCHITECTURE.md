# Civic Pulse - Architecture Overview

## System Flow

```
┌─────────────┐
│    USER     │
│  Dashboard  │
└──────┬──────┘
       │
       ├──> Reports Issue ──> ┌──────────────────┐
       │                      │  Reports (MongoDB)│
       │                      └────────┬─────────┘
       │                               │
       │                               ▼
       │                      ┌──────────────────┐
       │                      │ RAG Matcher      │
       │                      │ (NGO Matching)   │
       │                      └────────┬─────────┘
       │                               │
       │                               ▼
       ├──> Chatbot (RAG) <───┌──────────────────┐
       │                      │  Vector Store    │
       │                      │  (Issues, NGOs,  │
       │                      │   Site Info)     │
       │                      └──────────────────┘
       │
       └──> Apply as Volunteer ──> Applications Collection


┌─────────────┐
│     NGO     │
│  Dashboard  │
└──────┬──────┘
       │
       ├──> View Assigned Issues (from Issues array)
       ├──> Assign to Volunteers
       ├──> Manage Volunteers (create accounts)
       └──> Review Reports


┌─────────────┐
│  VOLUNTEER  │
│  Dashboard  │
└──────┬──────┘
       │
       ├──> View Assigned Issues (from assignedWorks array)
       └──> Update Issue Status


┌─────────────┐
│    ADMIN    │
│  Dashboard  │
└──────┬──────┘
       │
       ├──> Manage NGOs (CRUD)
       ├──> Create NGO Accounts
       ├──> Manage Volunteers
       └──> System Statistics
```

## Data Flow

### Issue Reporting Flow
1. User reports issue → Stored in `Reports` collection
2. RAG matcher analyzes issue → Compares with NGO Categories/Description
3. Best matching NGO assigned → Update `Reports.assignedTo` and `NGO.Issues`
4. NGO notified → Appears in NGO dashboard

### Chatbot Query Flow
1. User asks question → Sent to RAG system
2. Vector search → Finds relevant documents (Reports, NGO info, site info)
3. Context retrieval → Builds context from top matches
4. LLM generates answer → Returns to user
5. Chat history stored → For future reference

### Volunteer Assignment Flow
1. NGO views assigned issue from `NGO.Issues` array
2. NGO selects volunteer → Update `Reports.assignedTo` and `Volunteers.assignedWorks`
3. Volunteer sees issue in dashboard
4. Volunteer updates status → Update `Reports.Status`
5. Status propagated to User and NGO dashboards

## MongoDB Collections & Relationships

### Collections (exact naming from workflow document)

1. **User**
   - Stores user information
   - `Reported issues` → Array of Report ObjectIds

2. **Reports**
   - Stores all reported issues
   - `Username` → Reference to User
   - `assignedTo` → Array of [NGO, volunteers] references
   - `Status` → Enum: 'not verified', 'verified', 'assigned', 'in-progress', 'resolved'

3. **NGO**
   - Stores NGO information
   - `Issues` → Array of Report ObjectIds
   - `volunteers` → Array of Volunteer ObjectIds
   - `Applications` → Array of Application ObjectIds

4. **Volunteers**
   - Stores volunteer information
   - `NGO` → Reference to NGO ObjectId
   - `assignedWorks` → Array of Report ObjectIds

5. **Applications**
   - Stores user applications to join NGOs
   - `Username` → Reference to User
   - `NGOselected` → Reference to NGO ObjectId
   - `status` → Enum: 'pending', 'accepted', 'rejected'

6. **Admin**
   - Stores admin accounts

## Key Components

### 1. Authentication Layer
- Role-based access (User, NGO, Volunteer, Admin)
- Session management using Streamlit session state
- Secure password storage with bcrypt

### 2. RAG System
- Vector embeddings of:
  - All Reports (by location/site)
  - NGO profiles, Categories, and Description
  - Site/location information
  - General civic service information
- Similarity search for matching
- Context-aware responses

### 3. Database Layer
- MongoDB with PyMongo
- Collections follow exact naming from workflow document
- Relationships maintained through ObjectId references and arrays

### 4. Business Logic Layer
- Model classes for each collection
- Validation logic
- Business rules enforcement

## Technology Choices

- **Streamlit**: Rapid development, good for dashboards
- **MongoDB**: NoSQL database with flexible schema
- **PyMongo**: MongoDB Python driver
- **FAISS/ChromaDB**: Fast vector similarity search
- **Sentence Transformers**: Embedding generation
- **LangChain**: RAG pipeline orchestration
- **bcrypt**: Password hashing
