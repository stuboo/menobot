import streamlit as st
import requests
from openai import OpenAI
from openai.types.beta.assistant_stream_event import ThreadMessageDelta
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
from datetime import datetime

# Initialize OpenAI client and credentials
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ASSISTANT_ID_CHAT = st.secrets["ASSISTANT_ID_CHAT"]
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize session state to store conversation history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Set the app layout to wide
st.set_page_config(layout="wide")

# Custom CSS to fix the input box at the bottom
st.markdown(
    """
    <style>
    .main {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }
    .chat-container {
        flex: 1;
        overflow-y: auto;
        display: flex;
        flex-direction: column-reverse;
    }
    .input-box {
        position: fixed;
        bottom: 0;
        width: 100%;
        background: white;
        padding: 10px;
        z-index: 1000;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Chat with Assistant")

# Create a container for chat messages
chat_container = st.container()

# Display messages in chat history
with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    st.markdown('</div>', unsafe_allow_html=True)

# Textbox and streaming process for chat input
st.markdown('<div class="input-box">', unsafe_allow_html=True)
if user_query := st.chat_input("Ask me a question"):
    # Create a new thread if it does not exist
    if not st.session_state.thread_id:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    # Display the user's query
    with st.chat_message("user"):
        st.markdown(user_query)

    # Store the user's query into the history
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    # Add user query to the thread
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_query
    )

    # Stream the assistant's reply
    with st.chat_message("assistant"):
        stream = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID_CHAT,
            stream=True
        )

        # Empty container to display the assistant's reply
        assistant_reply_box = st.empty()

        # A blank string to store the assistant's reply
        assistant_reply = ""

        # Iterate through the stream and update assistant's reply
        for event in stream:
            if isinstance(event, ThreadMessageDelta):
                if event.data.delta.content and isinstance(event.data.delta.content[0], TextDeltaBlock):
                    assistant_reply += event.data.delta.content[0].text.value
                    assistant_reply_box.markdown(assistant_reply)

        # Once the stream is over, update chat history
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})
st.markdown('</div>', unsafe_allow_html=True)