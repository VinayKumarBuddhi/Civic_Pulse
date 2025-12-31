**Civic Pulse — RAG Chatbot Implementation**

This document describes the RAG-based chatbot service implementation and the functions that make up the pipeline. The implementation uses ChromaDB for persistent vector storage and SentenceTransformers (`all-MiniLM-L6-v2`) for embeddings.

**Prerequisites**
- Python packages installed (see `requirements.txt`). Important packages: `chromadb`, `sentence-transformers`, `streamlit`, `openai` (optional).
- MongoDB running and configured in `database/database.py`.
- (Optional) `OPENAI_API_KEY` set in environment for LLM responses.

**Files (entry points)**
- Vector store: [rag/vector_store.py](rag/vector_store.py)
- Embeddings helper: [rag/embeddings.py](rag/embeddings.py)
- Retrieval / context builder: [rag/ngo_matcher.py](rag/ngo_matcher.py)
- Chatbot orchestration and LLM wrapper: [services/chatbot_service.py](services/chatbot_service.py)
- Streamlit chat UI: [pages/5_Chatbot.py](pages/5_Chatbot.py)
- (Optional) index builder CLI: [rag/build_index.py](rag/build_index.py) — create if needed

**High-level runtime flow (exact sequence)**
1. Input the query (Streamlit UI) — user types question and submits.
2. Query processing (chat service) — sanitize and embed the query.
3. Vector DB similarity search — use ChromaDB to retrieve top-K documents.
4. Context retrieval — build a concise context block from retrieved snippets.
5. Prompt construction — combine query + context into a RAG-safe prompt.
6. LLM call — send prompt to LLM (OpenAI or fallback) and parse the result.
7. Display — show answer and structured recommendations in the chat UI.

**Module & Function Reference (what each function will do)**

**`rag/embeddings.py`**
- `_get_model()` — Lazily load and cache the `SentenceTransformer` model.
- `embed_texts(texts: List[str]) -> List[List[float]]` — Return embeddings for a list of texts. Used by retrievers or for batch indexing.

**`rag/vector_store.py`**
- `_get_chroma_client()` — Initialize or return existing ChromaDB `Client` (persistent directory: `vector_store`).
- `_normalize_metadata(d: dict) -> dict` — Convert lists/dicts into primitive strings acceptable to ChromaDB.
- `_build_ngo_text(ngo: dict) -> str` — Format NGO information into a single text chunk for embedding.
- `initialize_vector_store()` — Ensure client and collections exist and prepare embedding model.
- `create_all_ngo_embeddings()` — Bulk-create NGO embeddings (used for first-run or full rebuild). Should be extended to support `issues`, `sites`, `faq`.
- `add_ngo_to_vector_db(ngo_id: str)` — Incremental add when new NGO is created.
- `update_ngo_in_vector_db(ngo_id: str)` — Replace NGO vector when NGO updates.
- `remove_ngo_from_vector_db(ngo_id: str)` — Remove NGO vector when NGO is deleted/deactivated.
- `search_vector_db(query_text: str, top_k: int = 5, where: Optional[Dict] = None)` — Run a vector query (text → embedding internally) and return normalized hits. Note: this function already guards against empty `where` and prints diagnostics.

**`rag/ngo_matcher.py`**
- `_build_issue_text(report: dict) -> str` — Format issue text for embedding/indexing and matching.
- `search_similar_ngos(issue_description, issue_categories, ...) -> List[(ngo_id, score)]` — Formulates a query text and calls `search_vector_db()` to find similar NGOs (used in auto-assignment flows).
- `match_issue_to_ngo(report_id: str) -> Optional[str]` — Full pipeline to match a stored report to the best active NGO.
- (To add) `create_or_rebuild_index(sources=['issues','ngos','sites','faq'])` — Produce canonical IDs, metadata (include `type` and `source_id`) and call `collection.add()` in batches. This will be invoked by an admin CLI or on first run only.

**`services/chatbot_service.py`**
- `build_context(hits: List[dict], max_chars: int = 3000) -> str` — Build a concatenated, prioritized context string from retrieval hits (faq/site → issue → ngo) and trim to `max_chars`.
- `build_prompt(question: str, context: str) -> str` — Produce the RAG-safe prompt combining system instructions, context, and the user question.
- `call_llm(prompt: str, model='gpt-3.5-turbo') -> dict` — Call OpenAI if `OPENAI_API_KEY` present; otherwise use a lightweight fallback summarizer. Returns `{'text': ..., 'raw': ...}`.
- `parse_recommendations_from_hits(hits: List[dict]) -> List[dict]` — Convert retrieval hits to UI-friendly recommendation objects with fields: `id`, `type`, `score`, `snippet`, `metadata`.
- `chat_with_rag(question: str, top_k: int = 6, filters: Optional[dict] = None) -> dict` — End-to-end orchestration: retrieve → context → prompt → LLM → parse → return structured result: `{'answer', 'recommendations', 'references', 'raw'}`.

**`pages/5_Chatbot.py`**
- Provides the chat UI: input text, send button, and chat history in `st.session_state.chat_history`.
- On submit: calls `services.chatbot_service.chat_with_rag()` and stores `last_recommendations` in session for quick UI rendering.
- Renders recommendations with expanders and metadata; can be extended to add action buttons (contact, assign, open NGO profile).

**Indexing & ID conventions**
- Use canonical prefixes to allow multiple types in a single collection:
  - `issue:<issue_id>`
  - `ngo:<ngo_id>`
  - `site:<site_id>`
  - `faq:<faq_id>`
- Each metadata object must include `type` and `source_id` and should set `emb_model` (embedding model name) to help detect mismatches.

**Run & test**
1. Install requirements:

```cmd
pip install -r requirements.txt
# or install specific packages if not present:
pip install chromadb sentence-transformers openai streamlit
```

2. Populate/rebuild index (first run or when needed):

```cmd
python rag/build_index.py
# or call create_all_ngo_embeddings() from a small script
```

3. Run Streamlit app and open Chat page:

```cmd
streamlit run app.py
# then open the Chat page at the Streamlit UI
```

4. Diagnostics and tests:

```cmd
python rag/test_vector_store.py
```

**Operational notes & best practices**
- Avoid full rebuilds unless embedding model or metadata schema changes. Use incremental update functions (`add_*`, `update_*`, `remove_*`) on entity lifecycle events.
- Persist the Chroma client after bulk adds (call `client.persist()` if available). `rag/vector_store.py` contains guards for this.
- Limit context size for LLM prompts to avoid token overrun.
- Cache recent queries to reduce repeated LLM calls.
- Store API keys in env vars (`OPENAI_API_KEY`) and never commit them.

**Troubleshooting**
- If retrieval returns empty results, verify:
  - Chroma collection exists: check `vector_store` directory and `client.list_collections()`.
  - Index contains entries: run `rag/test_vector_store.py` to print counts.
  - Metadata types are primitives (use `_normalize_metadata()` to prevent Chroma validation errors).
- If embeddings are stale after model change, run a full rebuild and set `emb_model` metadata accordingly.

If you want, I can now:
- Add `rag/build_index.py` CLI and hook incremental calls into NGO create/update/delete flows, or
- Add unit tests and a small admin page to trigger rebuilds from the UI.

