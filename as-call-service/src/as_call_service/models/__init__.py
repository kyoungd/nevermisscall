"""Models package for as-call-service."""

from .call import (
    Call,
    CallCreate,
    CallUpdate,
    CallWebhook,
    CallResponse,
    CallListResponse,
)
from .conversation import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationSummary,
    ConversationResponse,
    ConversationListResponse,
    ConversationReplyRequest,
    ConversationReplyResponse,
)
from .message import (
    Message,
    MessageCreate,
    MessageUpdate,
    MessageWebhook,
    MessageResponse,
    MessageHistoryResponse,
)
from .lead import (
    Lead,
    LeadCreate,
    LeadUpdate,
    LeadStatusUpdate,
    LeadResponse,
    LeadListResponse,
    AIAnalysis,
)

__all__ = [
    # Call models
    "Call",
    "CallCreate",
    "CallUpdate", 
    "CallWebhook",
    "CallResponse",
    "CallListResponse",
    # Conversation models
    "Conversation",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationSummary",
    "ConversationResponse",
    "ConversationListResponse",
    "ConversationReplyRequest",
    "ConversationReplyResponse",
    # Message models
    "Message",
    "MessageCreate",
    "MessageUpdate",
    "MessageWebhook",
    "MessageResponse",
    "MessageHistoryResponse",
    # Lead models
    "Lead",
    "LeadCreate",
    "LeadUpdate",
    "LeadStatusUpdate",
    "LeadResponse",
    "LeadListResponse",
    "AIAnalysis",
]