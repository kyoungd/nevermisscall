"""
Conversation timeout management for fail-fast patterns.
Week 2, Day 4-5 implementation - handles conversation lifecycle and timeouts.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from threading import Lock

from dispatch_bot.models.basic_schemas import BasicDispatchResponse, ConversationStage

logger = logging.getLogger(__name__)


@dataclass
class ConversationTimeout:
    """Conversation timeout tracking information"""
    conversation_id: str
    started_at: datetime
    expires_at: datetime
    timeout_minutes: int
    last_activity: datetime
    warning_sent: bool = False


class ConversationManager:
    """
    Manages conversation lifecycle and timeouts.
    
    Key features:
    - Track conversation start and timeout times
    - Detect expired conversations
    - Generate timeout warning messages
    - Clean up expired conversations
    - Extend timeouts based on activity
    """
    
    def __init__(self, default_timeout_minutes: int = 5):
        """
        Initialize conversation manager.
        
        Args:
            default_timeout_minutes: Default timeout for conversations
        """
        self.default_timeout_minutes = default_timeout_minutes
        self.active_conversations: Dict[str, ConversationTimeout] = {}
        self._lock = Lock()  # Thread safety for conversation tracking
    
    def start_conversation(self, conversation_id: str, 
                          timeout_minutes: Optional[int] = None) -> ConversationTimeout:
        """
        Start tracking a new conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            timeout_minutes: Override default timeout
            
        Returns:
            ConversationTimeout object
        """
        timeout_minutes = timeout_minutes or self.default_timeout_minutes
        now = datetime.now()
        
        timeout_info = ConversationTimeout(
            conversation_id=conversation_id,
            started_at=now,
            expires_at=now + timedelta(minutes=timeout_minutes),
            timeout_minutes=timeout_minutes,
            last_activity=now
        )
        
        with self._lock:
            self.active_conversations[conversation_id] = timeout_info
        
        logger.info(f"Started conversation {conversation_id} with {timeout_minutes}min timeout")
        return timeout_info
    
    def update_activity(self, conversation_id: str) -> None:
        """
        Update last activity time for a conversation.
        
        Args:
            conversation_id: Conversation identifier
        """
        with self._lock:
            if conversation_id in self.active_conversations:
                self.active_conversations[conversation_id].last_activity = datetime.now()
    
    def extend_conversation_timeout(self, conversation_id: str, 
                                  additional_minutes: int) -> bool:
        """
        Extend conversation timeout.
        
        Args:
            conversation_id: Conversation identifier
            additional_minutes: Minutes to add to timeout
            
        Returns:
            True if extended, False if conversation not found
        """
        with self._lock:
            if conversation_id not in self.active_conversations:
                return False
            
            conversation = self.active_conversations[conversation_id]
            conversation.expires_at += timedelta(minutes=additional_minutes)
            conversation.timeout_minutes += additional_minutes
            
            logger.info(
                f"Extended conversation {conversation_id} timeout by {additional_minutes} minutes"
            )
            return True
    
    def is_conversation_expired(self, conversation_id: str) -> bool:
        """
        Check if conversation has expired.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if expired, False if active or not found
        """
        with self._lock:
            if conversation_id not in self.active_conversations:
                return True  # Unknown conversations are considered expired
            
            conversation = self.active_conversations[conversation_id]
            return datetime.now() >= conversation.expires_at
    
    def get_timeout_info(self, conversation_id: str) -> Optional[ConversationTimeout]:
        """
        Get timeout information for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            ConversationTimeout or None if not found
        """
        with self._lock:
            return self.active_conversations.get(conversation_id)
    
    def check_for_timeout_warning(self, conversation_id: str, 
                                business_name: str) -> Optional[BasicDispatchResponse]:
        """
        Check if conversation needs timeout warning.
        
        Args:
            conversation_id: Conversation identifier
            business_name: Business name for response
            
        Returns:
            Warning response or None if no warning needed
        """
        timeout_info = self.get_timeout_info(conversation_id)
        if not timeout_info or timeout_info.warning_sent:
            return None
        
        # Check if we're within 1 minute of timeout
        minutes_remaining = (timeout_info.expires_at - datetime.now()).total_seconds() / 60
        
        if minutes_remaining <= 1 and minutes_remaining > 0:
            # Mark warning as sent
            with self._lock:
                timeout_info.warning_sent = True
            
            logger.info(f"Sending timeout warning for conversation {conversation_id}")
            
            return BasicDispatchResponse(
                next_message=f"I haven't heard from you in a while. I'll be available for about {int(minutes_remaining)} more minute(s) if you'd like to continue, or you can call {business_name} directly.",
                conversation_stage=ConversationStage.COLLECTING_INFO,
                requires_followup=True,
                conversation_timeout_minutes=int(minutes_remaining)
            )
        
        return None
    
    def generate_timeout_response(self, conversation_id: str, 
                                business_name: str) -> BasicDispatchResponse:
        """
        Generate response for timed-out conversation.
        
        Args:
            conversation_id: Conversation identifier
            business_name: Business name for response
            
        Returns:
            Timeout response
        """
        logger.info(f"Generating timeout response for conversation {conversation_id}")
        
        return BasicDispatchResponse(
            next_message=f"Our conversation has timed out, but {business_name} is still here to help! Please start a new conversation or call us directly for immediate assistance.",
            conversation_stage=ConversationStage.TIMEOUT,
            requires_followup=False,
            conversation_timeout_minutes=0
        )
    
    def cleanup_expired_conversations(self) -> int:
        """
        Clean up expired conversations from tracking.
        
        Returns:
            Number of conversations cleaned up
        """
        now = datetime.now()
        expired_conversations = []
        
        with self._lock:
            for conversation_id, timeout_info in self.active_conversations.items():
                if now >= timeout_info.expires_at:
                    expired_conversations.append(conversation_id)
            
            for conversation_id in expired_conversations:
                del self.active_conversations[conversation_id]
        
        if expired_conversations:
            logger.info(f"Cleaned up {len(expired_conversations)} expired conversations")
        
        return len(expired_conversations)
    
    def complete_conversation(self, conversation_id: str) -> None:
        """
        Mark conversation as complete and remove from tracking.
        
        Args:
            conversation_id: Conversation identifier
        """
        with self._lock:
            if conversation_id in self.active_conversations:
                del self.active_conversations[conversation_id]
                logger.info(f"Completed conversation {conversation_id}")
    
    def get_active_conversation_count(self) -> int:
        """Get number of active conversations"""
        with self._lock:
            return len(self.active_conversations)
    
    def get_conversation_stats(self) -> Dict[str, int]:
        """
        Get conversation statistics.
        
        Returns:
            Dictionary with conversation statistics
        """
        now = datetime.now()
        stats = {
            "active_conversations": 0,
            "expiring_soon": 0,  # Within 1 minute
            "warnings_sent": 0
        }
        
        with self._lock:
            for timeout_info in self.active_conversations.values():
                stats["active_conversations"] += 1
                
                minutes_remaining = (timeout_info.expires_at - now).total_seconds() / 60
                if minutes_remaining <= 1:
                    stats["expiring_soon"] += 1
                
                if timeout_info.warning_sent:
                    stats["warnings_sent"] += 1
        
        return stats
    
    def _get_minutes_elapsed(self, conversation_id: str) -> Optional[float]:
        """
        Get minutes elapsed since conversation started (for testing).
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Minutes elapsed or None if not found
        """
        timeout_info = self.get_timeout_info(conversation_id)
        if not timeout_info:
            return None
        
        elapsed = datetime.now() - timeout_info.started_at
        return elapsed.total_seconds() / 60


# Global conversation manager instance
conversation_manager = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance"""
    return conversation_manager