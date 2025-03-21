import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from chat_session import ChatSession, Message
import asyncio
from terminal_manager import TerminalManager

class ChatManager:
    def __init__(self, storage_dir: str = "chat_sessions"):
        self.storage_dir = storage_dir
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        self.terminal_manager = TerminalManager()
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
    
    def _load_sessions(self):
        """Load all saved chat sessions from storage."""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        session = ChatSession.from_dict(data)
                        self.sessions[session.id] = session
                        
            # Set current session to the most recently updated one if exists
            if self.sessions:
                current = max(self.sessions.values(), key=lambda s: s.updated_at)
                self.current_session_id = current.id
        except Exception as e:
            print(f"Error loading sessions: {e}")
    
    def _save_session(self, session_id: str):
        """Save a specific chat session to storage."""
        try:
            session = self.sessions.get(session_id)
            if session:
                file_path = os.path.join(self.storage_dir, f"{session_id}.json")
                with open(file_path, 'w') as f:
                    json.dump(session.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")
    
    def create_session(self, title: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(title=title)
        self.sessions[session.id] = session
        self.current_session_id = session.id
        self._save_session(session.id)
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a specific chat session."""
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active chat session."""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def switch_session(self, session_id: str) -> bool:
        """Switch to a different chat session."""
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        if session_id in self.sessions:
            # Remove from memory
            del self.sessions[session_id]
            
            # Remove from storage
            file_path = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # If current session was deleted, switch to another or None
            if session_id == self.current_session_id:
                self.current_session_id = next(iter(self.sessions.keys())) if self.sessions else None
            
            return True
        return False
    
    def list_sessions(self) -> List[Dict]:
        """List all chat sessions with basic info."""
        return sorted([
            {
                'id': session.id,
                'title': session.title,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'message_count': len(session.messages)
            }
            for session in self.sessions.values()
        ], key=lambda x: x['updated_at'], reverse=True)
    
    async def add_message(self, role: str, content: str) -> Optional[Message]:
        """Add a message to the current session."""
        session = self.get_current_session()
        if session:
            message = session.add_message(role, content)
            self._save_session(session.id)
            return message
        return None
    
    def update_session_title(self, session_id: str, new_title: str) -> bool:
        """Update a chat session's title."""
        session = self.get_session(session_id)
        if session:
            session.update_title(new_title)
            self._save_session(session_id)
            return True
        return False
    
    def clear_session_messages(self, session_id: str) -> bool:
        """Clear all messages in a chat session."""
        session = self.get_session(session_id)
        if session:
            session.clear_messages()
            self._save_session(session_id)
            return True
        return False
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages from a specific session with optional limit."""
        session = self.get_session(session_id)
        if session:
            messages = session.get_messages()
            if limit is not None:
                return messages[-limit:]
            return messages
        return [] 