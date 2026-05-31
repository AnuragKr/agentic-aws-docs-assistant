from dataclasses import dataclass

from config.settings import Settings
from generation.service import GenerationService
from retrieval.reranker import CrossEncoderReranker
from retrieval.service import RetrievalService

from agent.conversation_summarizer import ConversationSummarizer
from agent.domain_guard import AWSDomainGuardService
from agent.intent import IntentClassifier
from agent.query_expansion import QueryExpansionService
from agent.query_rewriter import ConversationAwareQueryRewriter
from agent.tavily_tool import TavilySearchTool
from agent.tool_decision import ToolDecisionService
from infrastructure.aws.chat_memory import DynamoDBChatMemoryStore


@dataclass(frozen=True)
class AgentDependencies:
    settings: Settings
    domain_guard: AWSDomainGuardService
    intent_classifier: IntentClassifier
    query_rewriter: ConversationAwareQueryRewriter
    query_expansion: QueryExpansionService
    conversation_summarizer: ConversationSummarizer
    retrieval_service: RetrievalService
    reranker: CrossEncoderReranker | None
    tool_decision: ToolDecisionService
    tavily_tool: TavilySearchTool
    generation_service: GenerationService
    chat_memory: DynamoDBChatMemoryStore | None = None
