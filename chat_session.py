from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import uuid

@dataclass
class Message:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    terminal_state: Dict = field(default_factory=dict)  # Store terminal state if needed
    
    def add_message(self, role: str, content: str) -> Message:
        """Add a new message to the chat session."""
        message = Message(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message
    
    def get_messages(self) -> List[Message]:
        """Get all messages in the chat session."""
        return self.messages
    
    def clear_messages(self):
        """Clear all messages in the chat session."""
        self.messages = []
        self.updated_at = datetime.now()
    
    def update_title(self, new_title: str):
        """Update the chat session title."""
        self.title = new_title
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert the chat session to a dictionary for storage."""
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'messages': [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in self.messages
            ],
            'terminal_state': self.terminal_state
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        """Create a chat session from a dictionary."""
        session = cls(
            id=data['id'],
            title=data['title'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            terminal_state=data.get('terminal_state', {})
        )
        
        session.messages = [
            Message(
                role=msg['role'],
                content=msg['content'],
                timestamp=datetime.fromisoformat(msg['timestamp'])
            )
            for msg in data['messages']
        ]
        
        return session 