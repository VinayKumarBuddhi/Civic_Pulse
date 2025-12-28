# Issue Reporting & Assignment Flow - Implementation Process

## Overview
This document outlines the step-by-step process to implement the complete issue reporting, verification, and assignment flow.

**Important Notes:**
- **Vector DB is shared** for both **NGO matching** AND **Chatbot** (RAG)
- **Vector DB must be dynamic** - automatically updates when new NGO is registered
- **Category extraction only** - no complex NLP analysis needed
- **Severity Score** (0.0-10.0) - calculated during verification, determines processing priority

---

## Flow Diagram

```
User Reports Issue (with image)
    ↓
Step 1: Store in Database (Status: "not verified", severityScore: 0.0)
    ↓
Step 2: Extract Categories (from user-selected categories - already done)
    ↓
Step 3: Verify Issue (CNN Model validates if issue is real & significant)
    ↓
Step 4: Calculate Severity Score (0.0-10.0) based on verification results
    ↓
Step 5: Status → "verified" (if valid) + Update severityScore
    ↓
Step 6: Process Reports by Severity (Higher severity = Priority processing)
    ↓
Step 7: RAG-Based NGO Matching (Search shared vector DB for related NGOs)
    ↓
Step 8: Auto-assign to Best Matching NGO (Status → "assigned")
    ↓
Step 9: Update NGO's Issues array
    ↓
Step 10: NGO assigns to Volunteer (Status → "in-progress")
```

---

## Implementation Steps

### Step 1: Store Initial Issue Report
**Location:** `pages/1_User_Dashboard.py` - `render_report_issue_form()`

**What to do:**
- ✅ Already implemented (updated to include severityScore)
- User fills form and submits issue
- Issue is stored in Reports collection with:
  - Image (base64 encoded)
  - Description (user-provided)
  - Categories (user-selected) - **already extracted**
  - Status: "not verified"
  - **severityScore: 0.0** (initial value, will be calculated during verification)
  - Location, Address, etc.

**Action Required:** None (already working - schema updated)

---

### Step 2: Extract Categories (Already Done)
**Status:** ✅ Complete

- Categories are already extracted from user selection in the form
- No additional processing needed
- Categories will be used directly for matching in Step 5

---

### Step 3: Create Issue Verification Module (CNN Model)
**New File:** `services/issue_verifier.py` or `ml/issue_classifier.py`

**What to implement:**

#### 3.1: Setup CNN Model
- Choose approach:
  - **Option A:** Use pre-trained CNN model (e.g., ResNet, MobileNet)
  - **Option B:** Train custom CNN for civic issues
  - **Option C:** Use image classification API (e.g., Google Vision, AWS Rekognition)

#### 3.2: Verify Issue Image
- Decode base64 image
- Preprocess image (resize, normalize)
- Run through CNN model
- Classify:
  - Is there an actual issue in the image? (binary classification)
  - What type of issue? (if multi-class)
  - Severity assessment? (if model supports)

**Functions to create:**
```python
def verify_issue_image(image_base64: str, description: str) -> dict:
    """
    Verify if image contains a real issue using CNN model
    
    Returns:
    {
        'is_valid': bool,
        'confidence': float,
        'issue_type': str (optional),
        'severity_score': float (0.0-10.0)  # Calculated based on:
            - Image analysis (CNN output)
            - Issue type and size
            - Description keywords
            - Impact assessment
    }
    """
    pass

def calculate_severity_score(image_base64: str, description: str, categories: list) -> float:
    """
    Calculate severity score (0.0 to 10.0) based on:
    - CNN model output (issue size, type, confidence)
    - Description analysis (keywords indicating urgency)
    - Category importance (some categories may be weighted higher)
    - Historical data (similar issues' severity)
    
    Returns:
    float: Severity score between 0.0 (minor) and 10.0 (critical)
    """
    pass

def is_issue_significant(image_base64: str) -> bool:
    """
    Check if issue is significant enough to process
    (e.g., not a minor scratch, but actual infrastructure problem)
    """
    pass
```

#### 3.3: Calculate and Update Severity Score
- **Severity Score Calculation:**
  - Range: 0.0 to 10.0
  - Based on CNN model analysis, issue description, and categories
  - Higher score = Higher priority for processing
  
- **Severity Score Levels (Guideline):**
  - **0.0-2.0**: Minor issues (cosmetic, low impact)
  - **2.1-5.0**: Moderate issues (needs attention but not urgent)
  - **5.1-7.5**: Serious issues (significant impact, should be addressed soon)
  - **7.6-10.0**: Critical issues (urgent, high impact, safety concerns)

#### 3.4: Update Issue Status and Severity
- If verification passes: 
  - Update status to "verified"
  - Update severityScore with calculated value
- If verification fails: 
  - Keep status as "not verified"
  - Keep severityScore at 0.0

**When to call:**
- After Step 1 (after issue is stored)
- Automatically trigger after issue is stored
- Or use background job/queue system

**Action Required:**
1. Create `services/issue_verifier.py`
2. Add CNN model or API integration
3. Create verification function with severity score calculation
4. Add automatic verification trigger in issue creation flow
5. Update ReportsModel with severity score after verification

**Database Updates:**
- Reports collection now includes `severityScore` field (0.0-10.0)
- Use `ReportsModel.update_status_and_severity()` to update both at once

---

### Step 4: Process Reports by Severity Priority
**Location:** `services/issue_service.py` (new file)

**What to implement:**

#### 4.1: Severity-Based Processing Queue
- Reports should be processed based on severity score
- Higher severity = Higher priority
- Processing order: Critical (7.6-10.0) → Serious (5.1-7.5) → Moderate (2.1-5.0) → Minor (0.0-2.0)

**Functions to create:**
```python
def get_pending_verified_reports_by_severity():
    """
    Get all verified reports sorted by severity score (highest first)
    Only returns reports that are verified but not yet assigned
    
    Returns:
    List of reports sorted by severityScore (descending)
    """
    pass

def process_reports_by_priority():
    """
    Process verified reports in order of severity priority
    - Fetch verified reports sorted by severity
    - Process highest severity first
    - Trigger NGO matching and assignment
    """
    pass
```

**When to call:**
- After Step 3 (after issues are verified and severity calculated)
- Can be scheduled/triggered periodically
- Or triggered immediately after verification

---

### Step 5: Setup Shared Vector Database (For NGO Matching & Chatbot)
**Important:** Vector DB is shared between NGO matching and Chatbot

**New File:** `rag/vector_store.py`

**Note:** When matching NGOs, consider severity score - higher severity issues may need more capable/experienced NGOs

**What to implement:**

#### 4.1: Initialize Vector Store
- **Decision Required:** Choose vector DB (FAISS or ChromaDB)
- Initialize embeddings model (Sentence Transformers or OpenAI)
- Create vector database instance
- Vector DB contains:
  - **NGO embeddings** (for matching)
  - **Reports/Issues embeddings** (for chatbot context)
  - **General civic service information** (for chatbot)

#### 4.2: Create NGO Embeddings Function
- Create embeddings for all NGOs:
  - NGO Description
  - NGO Categories
  - NGO Location/Address
  - NGO past issues handled (optional)
- Store in shared vector DB

#### 4.3: Dynamic Vector DB Updates
**Critical Requirement:** Vector DB must automatically update when new NGO is registered

**When NGO is created/registered:**
1. Generate embedding for new NGO (using same model)
2. Add to vector DB immediately
3. Update index (if needed)

**When NGO is updated:**
1. Regenerate embedding with new data
2. Update existing entry in vector DB

**When NGO is deleted/deactivated:**
1. Remove from vector DB
2. Update index

**Integration Points:**
- **NGO Registration:** Hook into NGO creation (Admin Dashboard or registration page)
  - Automatically call `add_ngo_to_vector_db(ngo_id)` after NGO creation
- **NGO Update:** Hook into NGO profile updates
  - Automatically call `update_ngo_in_vector_db(ngo_id)` when NGO info changes
- **NGO Deletion:** Hook into NGO deletion/deactivation
  - Automatically call `remove_ngo_from_vector_db(ngo_id)`

**Example Integration:**
```python
# In Admin Dashboard or NGO registration flow
result = NGOModel.create_ngo(ngo_data)
if result.inserted_id:
    ngo_id = str(result.inserted_id)
    # Immediately add to vector DB
    add_ngo_to_vector_db(ngo_id)  # Automatic dynamic update
```

**Functions to create:**
```python
def initialize_vector_store():
    """
    Initialize vector database and embeddings model
    Shared by both NGO matcher and Chatbot
    """
    pass

def create_all_ngo_embeddings():
    """
    Create embeddings for all existing NGOs and store in vector DB
    Call on startup or when rebuilding index
    """
    pass

def add_ngo_to_vector_db(ngo_id: str):
    """
    Add single NGO to vector DB (called when new NGO is registered)
    Must be called automatically after NGO creation
    """
    pass

def update_ngo_in_vector_db(ngo_id: str):
    """
    Update NGO embedding in vector DB (if NGO info changes)
    """
    pass

def remove_ngo_from_vector_db(ngo_id: str):
    """
    Remove NGO from vector DB (if NGO is deleted/deactivated)
    """
    pass
```

---

### Step 6: Create RAG-Based NGO Matcher
**New File:** `rag/ngo_matcher.py`

**What to implement:**

#### 6.1: Create Issue Embedding
- Create embedding for the reported issue using same model as NGO embeddings:
  - Issue description
  - Categories (user-selected)
  - Location
  - **Severity score** (can be included as context or used for filtering)

#### 6.2: Similarity Search in Vector DB
- Search shared vector DB for similar NGOs
- Rank by similarity score
- Consider:
  - Category matching
  - Geographic proximity
  - Description similarity
  - **Severity score** (higher severity may require NGOs with better track record/capacity)

**Functions to create:**
```python
def search_similar_ngos(issue_description: str, issue_categories: list, 
                        issue_location: dict, top_k: int = 3) -> list:
    """
    Search shared vector DB for NGOs similar to the issue
    
    Returns:
    List of (NGO ID, similarity_score) tuples sorted by score
    """
    # 1. Create issue embedding
    # 2. Search vector DB using similarity
    # 3. Return top_k matches with scores
    pass

def match_issue_to_ngo(report_id: str) -> str:
    """
    Match issue to best NGO using RAG
    
    Returns:
    NGO ID of best match (or None if no match found)
    """
    # 1. Get issue details from Reports collection
    # 2. Call search_similar_ngos()
    # 3. Select best match (top result)
    # 4. Return NGO ID
    pass
```

**When to call:**
- After Step 4 (after reports are prioritized by severity)
- Process reports in severity order (highest first)
- Automatically trigger when status becomes "verified"

---

### Step 7: Auto-Assign Issue to NGO
**Location:** `services/issue_service.py` (new file) or update existing code

**What to implement:**

#### 5.1: Assign Issue to NGO
- Get best matching NGO from Step 4
- Update Reports collection:
  - Add NGO ObjectId to `assignedTo` array
  - Update Status to "assigned"
- Update NGO collection:
  - Add Report ObjectId to NGO's `Issues` array

**Functions to create:**
```python
def assign_issue_to_ngo(report_id: str, ngo_id: str):
    """
    Assign issue to NGO
    
    1. Update Reports.assignedTo = [ngo_id]
    2. Update Reports.Status = "assigned"
    3. Update NGO.Issues = [report_id] (append)
    """
    pass
```

**When to call:**
- After Step 6 (RAG matching)
- Automatic after verification and severity calculation
- Processed in priority order (highest severity first)

---

### Step 8: Update NGO Dashboard
**Location:** `pages/2_NGO_Dashboard.py`

**What to implement:**

#### 8.1: Display Auto-Assigned Issues
- ✅ Already implemented (should be updated to show severity score)
- NGO can see issues in "Assigned Issues" tab
- Issues appear automatically after Step 7
- **Enhancement:** Display severity score and sort by severity (highest first)

#### 8.2: Assign to Volunteer
- ✅ Already implemented
- NGO selects volunteer from dropdown
- Updates Reports.assignedTo (add volunteer ID)
- Updates Reports.Status to "in-progress"
- Updates Volunteer.assignedWorks
- **Note:** NGOs may want to assign higher severity issues to more experienced volunteers

**Action Required:** 
- Verify assignment flow works correctly
- Test that status updates properly
- Add severity score display in NGO dashboard
- Consider sorting/filtering by severity score

---

## Complete Implementation Checklist

### Phase 1: Shared Vector Database Setup
- [ ] Create `rag/vector_store.py`
- [ ] **Decision:** Choose vector DB (FAISS or ChromaDB?)
- [ ] **Decision:** Choose embedding model (Sentence Transformers or OpenAI?)
- [ ] Implement `initialize_vector_store()` function
- [ ] Implement `create_all_ngo_embeddings()` function
- [ ] Implement `add_ngo_to_vector_db()` function (for dynamic updates)
- [ ] Implement `update_ngo_in_vector_db()` function
- [ ] Implement `remove_ngo_from_vector_db()` function
- [ ] Hook into NGO registration to auto-update vector DB
- [ ] Test vector DB initialization and updates

### Phase 2: Issue Verification (CNN) & Severity Calculation
- [ ] Create `services/issue_verifier.py` or `ml/issue_classifier.py`
- [ ] Choose CNN model approach (pre-trained/custom/API)
- [ ] Implement `verify_issue_image()` function
- [ ] Implement `calculate_severity_score()` function
- [ ] Implement `is_issue_significant()` function
- [ ] Add automatic verification trigger
- [ ] Update ReportsModel to store severity scores
- [ ] Test image verification and severity calculation

### Phase 2.5: Severity-Based Processing Queue
- [ ] Create severity-based processing functions in `services/issue_service.py`
- [ ] Implement `get_pending_verified_reports_by_severity()`
- [ ] Implement `process_reports_by_priority()`
- [ ] Test priority processing

### Phase 3: RAG NGO Matching
- [ ] Create `rag/ngo_matcher.py`
- [ ] Implement `search_similar_ngos()` function (uses shared vector DB)
- [ ] Implement `match_issue_to_ngo()` function
- [ ] Consider severity score in matching logic
- [ ] Integrate with severity-based processing queue
- [ ] Test RAG matching accuracy

### Phase 4: Auto-Assignment
- [ ] Create `services/issue_service.py`
- [ ] Implement `assign_issue_to_ngo()` function
- [ ] Create workflow function that chains Steps 3-5
- [ ] Add automatic assignment trigger
- [ ] Test complete flow

### Phase 5: Testing & Integration
- [ ] Test complete flow end-to-end
- [ ] Test edge cases (no matching NGO, verification fails, etc.)
- [ ] Add error handling
- [ ] Add logging
- [ ] Performance optimization

---

## Detailed Implementation Plan

### File Structure to Create

```
services/
├── issue_verifier.py      (Step 3: CNN verification)
└── issue_service.py       (Step 6: Assignment orchestration)

rag/
├── vector_store.py        (Step 4: Shared vector DB for NGO matching & Chatbot)
├── ngo_matcher.py         (Step 5: RAG matching using shared vector DB)
├── chatbot.py             (Uses shared vector_store.py)
└── embeddings.py          (Optional: Embedding utilities)

ml/                       (Optional, if using custom models)
└── issue_classifier.py    (CNN model wrapper)
```

---

## Integration Points

### 1. Issue Creation Flow (User Dashboard)
**Current:** `pages/1_User_Dashboard.py` → `render_report_issue_form()`

**Modify to:**
```python
# After creating report
result = ReportsModel.create_report(report_data)
if result.inserted_id:
    report_id = str(result.inserted_id)
    
    # Step 3: Verify issue (async or background)
    verification_result = verify_issue_image(image_base64, description)
    
    if verification_result['is_valid']:
        # Calculate severity score
        severity_score = calculate_severity_score(
            image_base64, 
            description, 
            categories
        )
        
        # Update status to verified and set severity score
        ReportsModel.update_status_and_severity(
            report_id, 
            'verified', 
            severity_score
        )
        
        # Step 4: Add to priority processing queue (or process immediately)
        # Step 6 & 7: Match and assign to NGO using shared vector DB
        ngo_id = match_issue_to_ngo(report_id)
        if ngo_id:
            assign_issue_to_ngo(report_id, ngo_id)
```

### 2. NGO Registration Flow (Auto-update Vector DB)
**Location:** Admin Dashboard or NGO Registration

**Modify to:**
```python
# After creating NGO
result = NGOModel.create_ngo(ngo_data)
if result.inserted_id:
    ngo_id = str(result.inserted_id)
    
    # Automatically add NGO to vector DB
    add_ngo_to_vector_db(ngo_id)  # Dynamic update
```

### 3. Chatbot Integration (Uses Shared Vector DB)
**Location:** `rag/chatbot.py`

**Note:** Chatbot will also use the same `vector_store.py` for:
- Searching NGO information
- Searching issue/report context
- Retrieving relevant information for responses

**Integration:**
```python
# Chatbot uses same vector store
from rag.vector_store import search_vector_db

# Search for relevant context
context = search_vector_db(user_query, top_k=5)
```

### 4. Background Processing (Optional)
For better performance, use background jobs:
- After issue creation, queue verification task
- After verification, queue matching task
- After matching, queue assignment task

**Libraries:**
- `celery` with Redis/RabbitMQ
- Or simple background thread
- Or scheduled tasks

---

## Technology Choices (Decisions Required)

### For Shared Vector Database (Step 4):
**Decision Required:**
- **Option 1:** FAISS (Facebook AI Similarity Search)
  - Pros: Fast, local, no dependencies
  - Cons: In-memory (needs saving/loading), rebuild needed
- **Option 2:** ChromaDB
  - Pros: Persistent storage, easier updates, good for production
  - Cons: Additional dependency

**Decision Required:**
- **Option 1:** Sentence Transformers (local, free)
  - Pros: No API costs, privacy, offline
  - Cons: Larger model size, initial download
- **Option 2:** OpenAI Embeddings API
  - Pros: High quality, managed service
  - Cons: API costs, requires internet

### For Image Verification & Severity Calculation (Step 3):
- **Option 1:** Pre-trained CNN (ResNet, MobileNet) + fine-tuning
  - Can output confidence + issue type + size estimation
  - Combine with description analysis for severity score
- **Option 2:** Google Cloud Vision API
  - Provides labels, detection confidence
  - Combine with custom severity calculation logic
- **Option 3:** AWS Rekognition
  - Similar to Google Vision
- **Option 4:** Custom trained CNN model
  - Can be trained to directly output severity scores
  - More control but requires training data

**Severity Score Calculation:**
- **Approach 1:** Rule-based (CNN confidence + description keywords + category weights)
- **Approach 2:** ML model (train model to predict severity from image + text)
- **Approach 3:** Hybrid (combine CNN output with rule-based scoring)

### For RAG Matching (Step 5):
- Uses shared vector DB from Step 4
- **Search:** Cosine similarity or L2 distance
- Same embedding model used for both NGOs and Issues

---

## Priority Order

1. **High Priority:**
   - Step 4: Shared Vector Database Setup (foundation for matching & chatbot)
   - Step 5: RAG NGO Matching (core feature)
   - Step 6: Auto-assignment (core feature)
   - Dynamic vector DB updates (when NGO registers)

2. **Medium Priority:**
   - Step 3: CNN Verification (quality control)

3. **Low Priority:**
   - Background processing optimization
   - Advanced ML model training

---

## Next Steps

1. **Decision Required:** Choose Vector DB (FAISS vs ChromaDB)
2. **Decision Required:** Choose Embedding Model (Sentence Transformers vs OpenAI)
3. **Start with Shared Vector Database** (Step 4) - Foundation
4. **Implement RAG NGO Matching** (Step 5) - Core feature
5. **Implement Auto-Assignment** (Step 6) - Complete the flow
6. **Add Dynamic Updates** - Hook into NGO registration
7. **Add CNN Verification** (Step 3) - Quality control

---

## Questions/Decisions Required

1. **Vector DB:** FAISS (local, fast) or ChromaDB (persistent, easier updates)?
2. **Embedding Model:** Sentence Transformers (local, free) or OpenAI API (managed, paid)?
3. **CNN Model:** Pre-trained or custom trained? (for Step 3)
4. **Severity Score Calculation:** Rule-based, ML-based, or hybrid approach?
5. **Severity Score Thresholds:** What severity levels define "Critical", "Serious", etc.?
6. **Processing:** Synchronous or asynchronous/background?
7. **Priority Processing:** 
   - Process immediately after verification?
   - Use a queue system?
   - Batch process periodically?
8. **Fallback:** What if no matching NGO found? (keep as "verified" unassigned?)
9. **Vector DB Update Strategy:** 
   - Immediate on NGO registration? ✅ (Required)
   - Batch updates? (if needed for performance)
   - Rebuild index periodically? (optional optimization)
10. **Severity in Matching:** Should severity score influence NGO matching? (higher severity → more capable NGOs?)

---

## Testing Strategy

1. **Unit Tests:**
   - Test each function individually
   - Mock CNN model responses
   - Mock vector search results

2. **Integration Tests:**
   - Test complete flow end-to-end
   - Test with various issue types
   - Test edge cases

3. **Performance Tests:**
   - Measure verification time
   - Measure matching time
   - Optimize bottlenecks

