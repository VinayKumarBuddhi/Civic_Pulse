import streamlit as st
from services.chatbot_service import chat_with_rag

st.set_page_config(page_title="Civic Pulse - Chatbot", page_icon="🤖")

st.markdown("## 💬 Civic Pulse Chatbot")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_input("Ask a question about NGOs, issues, or civic services", key="chat_ui_input")
with col2:
    send = st.button("Send")
    clear = st.button("Clear Chat")

    if clear:
        st.session_state.chat_history = []
        st.session_state.last_recommendations = []
        # Also clear input box
        try:
            st.session_state.chat_ui_input = ""
        except Exception:
            pass

if send and user_input:
    # Append user message
    st.session_state.chat_history.append(("user", user_input))
    # Call RAG chatbot service
    result = chat_with_rag(user_input, top_k=6)
    # Append bot response
    st.session_state.chat_history.append(("bot", result.get("answer", "")))
    # Store last recommendations for UI
    st.session_state.last_recommendations = result.get("recommendations", [])

# Display chat history
for role, msg in st.session_state.chat_history:
    if role == "user":
        st.markdown(f"**You:** {msg}")
    else:
        st.markdown(f"**Bot:** {msg}")
    st.markdown("---")

# Show recommendations if available
if st.session_state.get("last_recommendations"):
    st.markdown("### Recommended NGOs / References")
    for rec in st.session_state.last_recommendations:
        title = rec.get("metadata", {}).get("username") or rec.get("metadata", {}).get("name") or rec.get("id")
        with st.expander(title):
            st.write("Type:", rec.get("type"))
            st.write("Score:", rec.get("score"))
            st.write("Snippet:", rec.get("snippet"))
            st.write("Metadata:")
            st.json(rec.get("metadata"))
            # Action buttons could be wired here (contact, assign, view profile)
