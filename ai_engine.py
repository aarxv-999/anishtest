import google.generativeai as genai
import streamlit as st
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

class AIEventAssistant:
    def __init__(self):
        self.initialize_ai()
        self.conversation_history = []
    
    def initialize_ai(self):
        """Initialize the AI model"""
        try:
            # Configure Gemini API
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                api_key = st.secrets['GEMINI_API_KEY']
            else:
                # For local development
                api_key = st.text_input("Enter Gemini API Key:", type="password")
                if not api_key:
                    st.warning("Please provide a Gemini API key to use AI features")
                    return
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.chat = self.model.start_chat(history=[])
            
        except Exception as e:
            st.error(f"AI initialization error: {str(e)}")
            self.model = None
            self.chat = None
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the event planning assistant"""
        return """You are an expert Event Planning Assistant for a smart restaurant management system. Your role is to help staff plan memorable events, parties, and themed nights.

CAPABILITIES:
- Suggest creative event themes and concepts
- Recommend decorations, costumes, and ambiance ideas  
- Create seating arrangements and layouts
- Filter and suggest menu items based on dietary preferences
- Provide timeline and planning guidance
- Offer cost-effective solutions

PERSONALITY:
- Enthusiastic and creative
- Professional yet approachable
- Detail-oriented and practical
- Always consider dietary restrictions and accessibility

RESPONSE FORMAT:
- Be conversational and engaging
- Provide specific, actionable suggestions
- When suggesting menus, ask about dietary preferences
- Always end with a follow-up question to keep the conversation flowing
- Use emojis sparingly but effectively

CONSTRAINTS:
- Focus on restaurant/dining events only
- Keep suggestions realistic and budget-conscious
- Always prioritize guest safety and comfort
- Respect cultural sensitivities in theme suggestions

Remember: You're helping create memorable experiences that will delight guests and showcase the restaurant's capabilities."""

    def generate_response(self, user_message: str, menu_items: List[Dict] = None, context: Dict = None) -> str:
        """
        Generate AI response for event planning
        
        Args:
            user_message: User's input message
            menu_items: Available menu items for suggestions
            context: Additional context (event details, preferences, etc.)
        
        Returns:
            AI assistant response
        """
        try:
            if not self.chat:
                return self._get_fallback_response(user_message)
            
            # Build context-aware prompt
            enhanced_prompt = self._build_enhanced_prompt(user_message, menu_items, context)
            
            # Generate response
            response = self.chat.send_message(enhanced_prompt)
            
            # Store in conversation history
            self.conversation_history.append({
                'user': user_message,
                'assistant': response.text,
                'timestamp': datetime.now()
            })
            
            return response.text
            
        except Exception as e:
            st.error(f"AI response error: {str(e)}")
            return self._get_fallback_response(user_message)
    
    def _build_enhanced_prompt(self, user_message: str, menu_items: List[Dict] = None, context: Dict = None) -> str:
        """Build an enhanced prompt with context and menu information"""
        
        prompt_parts = [self.get_system_prompt()]
        
        # Add menu context if available
        if menu_items:
            prompt_parts.append("\nAVAILABLE MENU ITEMS:")
            for item in menu_items[:10]:  # Limit to prevent token overflow
                dietary_info = ", ".join(item.get('dietType', []))
                prompt_parts.append(f"- {item['name']} (${item['price']}) - {item['category']} - Dietary: {dietary_info}")
        
        # Add conversation context
        if context:
            prompt_parts.append(f"\nCONTEXT: {json.dumps(context, indent=2)}")
        
        # Add recent conversation history
        if len(self.conversation_history) > 0:
            prompt_parts.append("\nRECENT CONVERSATION:")
            for entry in self.conversation_history[-3:]:  # Last 3 exchanges
                prompt_parts.append(f"User: {entry['user']}")
                prompt_parts.append(f"Assistant: {entry['assistant'][:200]}...")  # Truncate for brevity
        
        prompt_parts.append(f"\nCURRENT USER MESSAGE: {user_message}")
        prompt_parts.append("\nPlease provide a helpful, creative response as the Event Planning Assistant:")
        
        return "\n".join(prompt_parts)
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Provide fallback responses when AI is unavailable"""
        
        fallback_responses = {
            'greeting': "Hello! I'm your Event Planning Assistant! 🎉 I'd love to help you create an amazing event. What type of celebration are you planning?",
            'birthday': "Birthday parties are my favorite! 🎂 For a memorable birthday celebration, consider:\n\n• **Theme Ideas**: Vintage Hollywood, Garden Party, or Decade-themed (80s, 90s)\n• **Decorations**: Balloon arches, string lights, personalized banners\n• **Menu**: I'd recommend a mix of appetizers, a signature main course, and a show-stopping dessert!\n\nHow many guests are you expecting?",
            'theme': "Great question about themes! Here are some popular options:\n\n🎭 **Elegant Themes**: Masquerade, Great Gatsby, Wine & Dine\n🌍 **Cultural Themes**: Mediterranean Night, Asian Fusion, Mexican Fiesta\n🎨 **Fun Themes**: Retro Diner, Garden to Table, Game Night\n\nWhat vibe are you going for - elegant, casual, or fun?",
            'menu': "For menu planning, I always start with dietary preferences! 🍽️\n\nLet me know if you need:\n• Vegetarian/Vegan options\n• Gluten-free selections\n• Kid-friendly choices\n• Specific cuisine types\n\nWhat dietary considerations should we keep in mind?",
            'default': "I'm here to help you plan an amazing event! 🌟 I can assist with themes, decorations, menu selection, and seating arrangements. What aspect of your event would you like to focus on first?"
        }
        
        # Simple keyword matching for fallback responses
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['hello', 'hi', 'start', 'help']):
            return fallback_responses['greeting']
        elif any(word in message_lower for word in ['birthday', 'bday']):
            return fallback_responses['birthday']
        elif any(word in message_lower for word in ['theme', 'decoration', 'decor']):
            return fallback_responses['theme']
        elif any(word in message_lower for word in ['menu', 'food', 'eat', 'dietary']):
            return fallback_responses['menu']
        else:
            return fallback_responses['default']
    
    def extract_event_details(self, conversation_text: str) -> Dict[str, Any]:
        """
        Extract structured event details from conversation
        
        Args:
            conversation_text: Full conversation or latest message
        
        Returns:
            Dictionary with extracted event details
        """
        
        event_details = {
            'eventType': None,
            'guestCount': None,
            'theme': None,
            'dietaryPreferences': [],
            'specialRequests': [],
            'budget': None,
            'date': None
        }
        
        text_lower = conversation_text.lower()
        
        # Extract event type
        event_types = ['birthday', 'anniversary', 'wedding', 'corporate', 'party', 'celebration', 'dinner', 'lunch']
        for event_type in event_types:
            if event_type in text_lower:
                event_details['eventType'] = event_type
                break
        
        # Extract guest count
        import re
        guest_patterns = [
            r'(\d+)\s*(?:people|guests|persons)',
            r'(?:for|around|about)\s*(\d+)',
            r'(\d+)\s*(?:pax|attendees)'
        ]
        
        for pattern in guest_patterns:
            match = re.search(pattern, text_lower)
            if match:
                event_details['guestCount'] = int(match.group(1))
                break
        
        # Extract dietary preferences
        dietary_keywords = {
            'vegan': ['vegan'],
            'vegetarian': ['vegetarian', 'veggie'],
            'gluten-free': ['gluten-free', 'gluten free', 'celiac'],
            'dairy-free': ['dairy-free', 'dairy free', 'lactose'],
            'low-carb': ['low-carb', 'low carb', 'keto'],
            'halal': ['halal'],
            'kosher': ['kosher']
        }
        
        for diet_type, keywords in dietary_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                event_details['dietaryPreferences'].append(diet_type)
        
        # Extract theme hints
        theme_keywords = ['retro', 'vintage', 'modern', 'rustic', 'elegant', 'casual', 'formal', 'themed']
        for keyword in theme_keywords:
            if keyword in text_lower:
                event_details['theme'] = keyword
                break
        
        return event_details
    
    def suggest_menu_items(self, menu_items: List[Dict], event_details: Dict, max_items: int = 6) -> List[Dict]:
        """
        Suggest menu items based on event details and dietary preferences
        
        Args:
            menu_items: Available menu items
            event_details: Extracted event information
            max_items: Maximum number of items to suggest
        
        Returns:
            List of suggested menu items
        """
        
        if not menu_items:
            return []
        
        suggested_items = []
        dietary_prefs = event_details.get('dietaryPreferences', [])
        guest_count = event_details.get('guestCount', 0)
        
        # Filter by dietary preferences if specified
        if dietary_prefs:
            filtered_items = []
            for item in menu_items:
                item_diets = item.get('dietType', [])
                if any(pref in item_diets for pref in dietary_prefs):
                    filtered_items.append(item)
            menu_items = filtered_items if filtered_items else menu_items
        
        # Ensure variety across categories
        categories_covered = set()
        for item in menu_items:
            if len(suggested_items) >= max_items:
                break
            
            category = item.get('category', 'Other')
            if len(categories_covered) < 3 or category not in categories_covered:
                suggested_items.append(item)
                categories_covered.add(category)
        
        return suggested_items[:max_items]
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        if self.chat:
            self.chat = self.model.start_chat(history=[])

# Singleton instance
ai_assistant = AIEventAssistant()
