import streamlit as st
import requests
from openai import OpenAI
from openai.types.beta.assistant_stream_event import ThreadMessageDelta
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
from datetime import datetime

# Initialize OpenAI client and credentials
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ASSISTANT_ID_CHAT = st.secrets["ASSISTANT_ID_CHAT"]
ASSISTANT_ID_EVAL = st.secrets["ASSISTANT_ID_EVAL"]
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize session state to store conversation history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Your PHP API URL for logging
PHP_API_URL = "https://tools.ryanstewart.com/log.php"


# Function to send logs to the PHP API
def send_log_to_php_api(conversation, evaluation):
    payload = {
        "conversation": conversation,
        "evaluation": evaluation
    }

    try:
        response = requests.post(PHP_API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                st.success("Conversation and evaluation logged successfully.")
            else:
                st.error(f"Failed to log: {data['message']}")
        else:
            st.error(f"Error: {response.status_code}")
    except Exception as e:
        st.error(f"An error occurred: {e}")


# Set the app layout to wide
st.set_page_config(layout="wide")

# Define app tabs
tab1, tab2 = st.tabs(["Examine", "Evaluate"])

# Examine tab - Chat with assistant
with tab1:
    st.header("Chat with Assistant")

    # Display messages in chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Textbox and streaming process for chat input
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

# Evaluate tab - Log of the conversation and evaluation button
with tab2:
    st.header("Evaluate Conversation Log")

    # Display the conversation log
    conversation_log = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.chat_history])
    st.text_area("Conversation Log", conversation_log, height=300, disabled=True)

    # Button to evaluate conversation log
    if st.button("EVALUATE RESPONSES"):
        if st.session_state.chat_history:
            # Prepare the conversation history as a single block of text
            log_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.chat_history])

            # Run the evaluation using the second assistant
            eval_run = client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,  # Reuse the thread
                assistant_id=ASSISTANT_ID_EVAL,
                stream=True  # Keep streaming mode to capture response
            )

            # Collect the evaluation result
            eval_response = ""
            eval_reply_box = st.empty()

            for event in eval_run:
                if isinstance(event, ThreadMessageDelta):
                    if event.data.delta.content and isinstance(event.data.delta.content[0], TextDeltaBlock):
                        eval_response += event.data.delta.content[0].text.value
                        eval_reply_box.markdown(eval_response)

            # Check if any response was collected
            if not eval_response.strip():
                st.error("No evaluation response received.")
            else:
                # Send the conversation and evaluation to the PHP API
                send_log_to_php_api(conversation_log, eval_response)

                # Show the evaluation response in a modal window (Streamlit popover)
                st.success("Evaluation Result:")
                st.markdown(f"<div class='popover'><p>{eval_response}</p></div>", unsafe_allow_html=True)