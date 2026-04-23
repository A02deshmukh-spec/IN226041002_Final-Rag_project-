import streamlit as st
import uuid
import os
from chatbot import build_graph
from dotenv import load_dotenv

# Set page configuration for a premium look
st.set_page_config(
    page_title="SkyLine Support AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

load_dotenv()

# Custom CSS for a sleek, premium design
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stStatusWidget {
        border-radius: 10px;
    }
    .st-emotion-cache-1c7n2ka {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
    }
    h1 {
        background: linear-gradient(90deg, #3b82f6, #9333ea);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "app" not in st.session_state:
    st.session_state.app = build_graph()
if "awaiting_hitl" not in st.session_state:
    st.session_state.awaiting_hitl = False

app = st.session_state.app
config = {"configurable": {"thread_id": st.session_state.thread_id}}

st.title("SkyLine Support AI")
st.markdown("---")

# 2. Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Handle HITL (Override) Input if active
if st.session_state.awaiting_hitl:
    with st.sidebar:
        st.warning("🚨 Escalation Required")
        st.info(f"The automated system requires human intervention for the last query.")
        hitl_input = st.text_area("Human Agent Response:", key="hitl_input_field", placeholder="Type the expert answer here...")
        if st.button("Submit Override Response"):
            if hitl_input:
                # Update graph state with human response
                app.update_state(config, {"hitl_response": hitl_input})
                
                # Resume graph
                with st.spinner("Resuming with your input..."):
                    for event in app.stream(None, config, stream_mode="values"):
                        pass
                
                # Get final answer
                final_state = app.get_state(config).values
                answer = final_state.get('generation', 'Error: No generation found.')
                
                # Add to chat history
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.awaiting_hitl = False
                st.rerun()
            else:
                st.error("Please provide a response before submitting.")

# 4. Main Chat Input
if prompt := st.chat_input("Ask a question about our services..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process Query
    with st.chat_message("assistant"):
        with st.status("Thinking...", expanded=True) as status:
            # We use a progress placeholder inside the status
            progress_text = st.empty()
            
            initial_state = {
                "question": prompt,
                "hitl_response": "",
                "generation": ""
            }
            
            # Execute graph and show progress
            for event in app.stream(initial_state, config, stream_mode="values"):
                if "intent" in event:
                    progress_text.text(f"🔍 Analyzing intent: {event['intent'].capitalize()}")
                if "documents" in event:
                    progress_text.text(f"📖 Found {len(event['documents'])} relevant docs...")
                if "generation" in event:
                    progress_text.text("✍️ Drafting answer...")
            
            status.update(label="Complete!", state="complete", expanded=False)
        
        # Check for HITL
        state = app.get_state(config)
        if state.next and state.next[0] == "hitl_node":
            st.session_state.awaiting_hitl = True
            st.markdown("*I'm checking this with our executive team. Please hold on...*")
            st.warning("⚠️ Escalated to Human Agent. See sidebar to provide override.")
            st.rerun()
        else:
            answer = state.values.get('generation', "I don't have an answer for that yet.")
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**System Architecture**")
st.sidebar.info("RAG + LangGraph (HITL)")
if st.sidebar.button("Clear Conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.awaiting_hitl = False
    st.rerun()
