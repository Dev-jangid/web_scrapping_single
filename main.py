import streamlit as st
from groq import Groq
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, get_groq_client, VECTOR_STORE_DIR
from session_manager import init_session_state, create_session, add_to_history
from web_utils import fetch_website_content, process_content
from vector_utils import vector_store_exists, retrieve_context
from groq_utils import generate_chat_response

# Initialize session state
init_session_state()

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)

def clear_vector_db():
    "Helper to clear vector database files"
    count = 0
    try:
        for file in VECTOR_STORE_DIR.glob("*"):
            file.unlink()
            count += 1
        return count
    except Exception as e:
        st.error(f"Error clearing database: {str(e)}")
        return 0

# Initialize Groq client
try:
    client = get_groq_client()
except Exception as e:
    st.error(str(e))
    st.stop()

# Load embedding model
embedding_model = load_embedding_model()

# Streamlit app layout
st.set_page_config(
    page_title="WebChat Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main Chat Area
st.title("WebChat Assistant")

# Check if a session is active
if st.session_state.current_session is None:
    # --- Landing Page: Start New Chat ---
    
    with st.form("new_session_form"):
        url = st.text_input("Website URL:")
        submit_new = st.form_submit_button("Start Chat", use_container_width=True)
        
        if submit_new and url:
            if not url.startswith('http'):
                st.error("Please enter a valid URL starting with http:// or https://")
            else:
                try:
                    raw_text = fetch_website_content(url)
                    if not raw_text:
                        st.error("Failed to fetch content from URL")
                    else:
                        processed_text = process_content(raw_text)
                        
                        # Show cache status
                        if vector_store_exists(url):
                            st.info("Using cached vector database")
                        else:
                            st.info("Creating new vector database")
                        
                        # Clear specific session data handling to enforce single session focus
                        st.session_state.sessions = {}
                        
                        new_session = create_session(url, processed_text, embedding_model)
                        session_id = new_session['id']
                        
                        st.session_state.sessions[session_id] = new_session
                        st.session_state.current_session = session_id
                        st.session_state.new_url = ""
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    

else:
    # --- Active Chat Session ---
    session = st.session_state.sessions[st.session_state.current_session]
    
    # Header with Controls
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.info(f"**Website:** {session['url']}")
    with col2:
        if st.button("Start New Chat", use_container_width=True):
            st.session_state.current_session = None
            st.rerun()
    with col3:
        if st.button("Clear Data", type="secondary", use_container_width=True):
            count = clear_vector_db()
            st.success(f"Cleared {count} files.")
            st.session_state.current_session = None
            st.rerun()
    
    # Chat History
    st.subheader("Chat History")
    
    for exchange in session['history']:
        with st.chat_message("user"):
            st.write(exchange['user'])
        with st.chat_message("assistant"):
            st.write(exchange['bot'])

    # Chat Input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Your question:", 
                                placeholder="Ask about this website...",
                                key="user_input")
        
        submit_chat = st.form_submit_button("Send", use_container_width=True)

        if submit_chat and user_input:
            try:
                # Retrieve context
                context = retrieve_context(
                    user_input, 
                    session['vector_store'], 
                    session['chunks'], 
                    embedding_model
                )
                
                # Generate response
                bot_response = generate_chat_response(
                    client,
                    user_input, 
                    context,
                    session['history']
                )
                
                # Store interaction
                session = add_to_history(session, user_input, bot_response)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()














































