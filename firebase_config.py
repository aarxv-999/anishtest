import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class FirestoreManager:
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._db is None:
            self.initialize_firestore()
    
    def initialize_firestore(self):
        """Initialize Firestore connection"""
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # For Streamlit Cloud deployment, use service account key from secrets
                if hasattr(st, 'secrets') and 'firebase' in st.secrets:
                    # Use Streamlit secrets for deployment
                    key_dict = dict(st.secrets["firebase"])
                    cred = credentials.Certificate(key_dict)
                else:
                    # For local development, use service account file
                    cred = credentials.Certificate('path/to/serviceAccountKey.json')
                
                firebase_admin.initialize_app(cred)
            
            self._db = firestore.client()
            st.success("✅ Firestore connected successfully!")
            
        except Exception as e:
            st.error(f"❌ Failed to connect to Firestore: {str(e)}")
            # Initialize with mock data for demo purposes
            self._db = None
    
    def get_db(self):
        """Get Firestore database instance"""
        return self._db
    
    def get_menu_items(self, diet_filters: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch menu items from Firestore with optional dietary filters
        
        Args:
            diet_filters: List of dietary preferences (e.g., ['vegan', 'gluten-free'])
        
        Returns:
            List of menu items
        """
        try:
            if self._db is None:
                return self._get_mock_menu_items(diet_filters)
            
            collection_ref = self._db.collection('menuItems')
            query = collection_ref
            
            # Apply dietary filters if provided
            if diet_filters:
                query = query.where('dietType', 'array_contains_any', diet_filters)
            
            docs = query.stream()
            menu_items = []
            
            for doc in docs:
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                menu_items.append(item_data)
            
            return menu_items
            
        except Exception as e:
            st.error(f"Error fetching menu items: {str(e)}")
            return self._get_mock_menu_items(diet_filters)
    
    def _get_mock_menu_items(self, diet_filters: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Mock menu items for demo/testing purposes"""
        mock_items = [
            {
                'id': '1',
                'name': 'Classic Caesar Salad',
                'category': 'Appetizers',
                'ingredients': ['romaine lettuce', 'parmesan', 'croutons', 'caesar dressing'],
                'dietType': ['vegetarian'],
                'price': 12.99,
                'imageURL': 'https://example.com/caesar.jpg'
            },
            {
                'id': '2',
                'name': 'Grilled Salmon',
                'category': 'Main Course',
                'ingredients': ['atlantic salmon', 'lemon', 'herbs', 'vegetables'],
                'dietType': ['gluten-free'],
                'price': 24.99,
                'imageURL': 'https://example.com/salmon.jpg'
            },
            {
                'id': '3',
                'name': 'Quinoa Buddha Bowl',
                'category': 'Main Course',
                'ingredients': ['quinoa', 'avocado', 'chickpeas', 'kale', 'tahini'],
                'dietType': ['vegan', 'gluten-free'],
                'price': 16.99,
                'imageURL': 'https://example.com/buddha-bowl.jpg'
            },
            {
                'id': '4',
                'name': 'Chocolate Lava Cake',
                'category': 'Desserts',
                'ingredients': ['dark chocolate', 'butter', 'eggs', 'flour', 'vanilla'],
                'dietType': ['vegetarian'],
                'price': 8.99,
                'imageURL': 'https://example.com/lava-cake.jpg'
            },
            {
                'id': '5',
                'name': 'Vegan Mushroom Risotto',
                'category': 'Main Course',
                'ingredients': ['arborio rice', 'mushrooms', 'nutritional yeast', 'vegetable broth'],
                'dietType': ['vegan', 'gluten-free'],
                'price': 18.99,
                'imageURL': 'https://example.com/risotto.jpg'
            }
        ]
        
        if diet_filters:
            filtered_items = []
            for item in mock_items:
                if any(diet in item['dietType'] for diet in diet_filters):
                    filtered_items.append(item)
            return filtered_items
        
        return mock_items
    
    def save_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Save event to Firestore
        
        Args:
            event_data: Event information dictionary
        
        Returns:
            Success status
        """
        try:
            if self._db is None:
                # Mock save for demo
                st.session_state.setdefault('mock_events', []).append(event_data)
                return True
            
            event_data['timestamp'] = datetime.now()
            doc_ref = self._db.collection('events').add(event_data)
            return True
            
        except Exception as e:
            st.error(f"Error saving event: {str(e)}")
            return False
    
    def get_events(self, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch events from Firestore
        
        Args:
            created_by: Optional filter by creator
        
        Returns:
            List of events
        """
        try:
            if self._db is None:
                return st.session_state.get('mock_events', [])
            
            collection_ref = self._db.collection('events')
            query = collection_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            if created_by:
                query = query.where('createdBy', '==', created_by)
            
            docs = query.stream()
            events = []
            
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            st.error(f"Error fetching events: {str(e)}")
            return []
    
    def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics for gamification features"""
        try:
            events = self.get_events()
            
            # Calculate stats
            total_events = len(events)
            creators = {}
            
            for event in events:
                creator = event.get('createdBy', 'Anonymous')
                creators[creator] = creators.get(creator, 0) + 1
            
            # Sort creators by event count
            top_creators = sorted(creators.items(), key=lambda x: x[1], reverse=True)
            
            return {
                'total_events': total_events,
                'top_creators': top_creators[:5],  # Top 5 creators
                'this_month': len([e for e in events if self._is_this_month(e.get('timestamp'))]) if events else 0
            }
            
        except Exception as e:
            st.error(f"Error calculating stats: {str(e)}")
            return {'total_events': 0, 'top_creators': [], 'this_month': 0}
    
    def _is_this_month(self, timestamp) -> bool:
        """Check if timestamp is from current month"""
        if not timestamp:
            return False
        
        try:
            if hasattr(timestamp, 'month'):
                return timestamp.month == datetime.now().month
            return False
        except:
            return False

# Singleton instance
firestore_manager = FirestoreManager()
