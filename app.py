import streamlit as st
import json
from datetime import datetime, date
from typing import Dict, List, Any
import pandas as pd

# Import our custom modules
from firebase_config import firestore_manager
from ai_engine import ai_assistant

# Page configuration
st.set_page_config(
    page_title="Event Manager - Smart Restaurant Assistant",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main > div {
        padding: 1rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #1f77b4;
    }
    
    .assistant-message {
        background-color: #e8f4fd;
        border-left-color: #17becf;
    }
    
    .event-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    
    .dietary-tag {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.1rem;
        display: inline-block;
    }
    
    .menu-item-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_event_details' not in st.session_state:
        st.session_state.current_event_details = {}
    
    if 'user_name' not in st.session_state:
        st.session_state.user_name = "Event Planner"

def display_chat_message(message: str, is_user: bool = True):
    """Display a chat message with proper styling"""
    css_class = "user-message" if is_user else "assistant-message"
    sender = "👤 You" if is_user else "🤖 Assistant"
    
    st.markdown(f"""
    <div class="chat-message {css_class}">
        <strong>{sender}:</strong><br>
        {message}
    </div>
    """, unsafe_allow_html=True)

def display_menu_item(item: Dict[str, Any]):
    """Display a menu item card"""
    dietary_tags = "".join([f'<span class="dietary-tag">{diet}</span>' for diet in item.get('dietType', [])])
    
    st.markdown(f"""
    <div class="menu-item-card">
        <h4>{item['name']} - ${item['price']}</h4>
        <p><strong>Category:</strong> {item['category']}</p>
        <p><strong>Ingredients:</strong> {', '.join(item.get('ingredients', []))}</p>
        <div>{dietary_tags}</div>
    </div>
    """, unsafe_allow_html=True)

def main_chat_interface():
    """Main chat interface for event planning"""
    st.header("🎉 Event Planning Assistant")
    st.write("Let me help you plan the perfect event! Tell me what you have in mind.")
    
    # Chat history display
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.chat_history:
            # Initial greeting
            display_chat_message(
                "Hello! I'm your Event Planning Assistant! 🎉 I'm here to help you create amazing events. "
                "What kind of celebration are you planning?", 
                is_user=False
            )
        
        # Display conversation history
        for chat in st.session_state.chat_history:
            display_chat_message(chat['message'], chat['is_user'])
    
    # User input section
    st.markdown("---")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_message = st.text_area(
            "Type your message:",
            key="user_input",
            height=100,
            placeholder="e.g., I want to plan a birthday party for 25 people with a retro theme..."
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        send_button = st.button("Send 💬", type="primary", use_container_width=True)
        clear_button = st.button("Clear Chat 🗑️", use_container_width=True)
    
    # Handle user input
    if send_button and user_message.strip():
        # Add user message to history
        st.session_state.chat_history.append({
            'message': user_message,
            'is_user': True,
            'timestamp': datetime.now()
        })
        
        # Extract event details from conversation
        full_conversation = " ".join([chat['message'] for chat in st.session_state.chat_history])
        event_details = ai_assistant.extract_event_details(full_conversation)
        st.session_state.current_event_details.update(event_details)
        
        # Get relevant menu items based on dietary preferences
        dietary_prefs = event_details.get('dietaryPreferences', [])
        menu_items = firestore_manager.get_menu_items(dietary_prefs if dietary_prefs else None)
        
        # Generate AI response
        with st.spinner("Thinking... 🤔"):
            ai_response = ai_assistant.generate_response(
                user_message, 
                menu_items, 
                st.session_state.current_event_details
            )
        
        # Add AI response to history
        st.session_state.chat_history.append({
            'message': ai_response,
            'is_user': False,
            'timestamp': datetime.now()
        })
        
        # Clear input and rerun
        st.session_state.user_input = ""
        st.rerun()
    
    # Clear chat functionality
    if clear_button:
        st.session_state.chat_history = []
        st.session_state.current_event_details = {}
        ai_assistant.clear_conversation()
        st.rerun()

def event_summary_sidebar():
    """Display current event details in sidebar"""
    st.sidebar.header("📋 Current Event Details")
    
    details = st.session_state.current_event_details
    
    if details:
        if details.get('eventType'):
            st.sidebar.write(f"**Event Type:** {details['eventType'].title()}")
        
        if details.get('guestCount'):
            st.sidebar.write(f"**Guest Count:** {details['guestCount']}")
        
        if details.get('theme'):
            st.sidebar.write(f"**Theme:** {details['theme'].title()}")
        
        if details.get('dietaryPreferences'):
            prefs = ", ".join(details['dietaryPreferences'])
            st.sidebar.write(f"**Dietary Preferences:** {prefs}")
        
        # Save event button
        st.sidebar.markdown("---")
        
        # Additional event details form
        with st.sidebar.form("save_event_form"):
            st.write("**Finalize Event Details:**")
            
            event_date = st.date_input("Event Date:", min_value=date.today())
            creator_name = st.text_input("Your Name:", value=st.session_state.user_name)
            additional_notes = st.text_area("Additional Notes:", height=100)
            
            save_button = st.form_submit_button("💾 Save Event", type="primary")
            
            if save_button:
                # Prepare event data for saving
                event_data = {
                    **details,
                    'date': event_date.isoformat(),
                    'createdBy': creator_name,
                    'additionalNotes': additional_notes,
                    'chatHistory': st.session_state.chat_history[-5:],  # Save last 5 messages
                    'timestamp': datetime.now()
                }
                
                # Save to Firestore
                if firestore_manager.save_event(event_data):
                    st.sidebar.success("✅ Event saved successfully!")
                    st.session_state.user_name = creator_name
