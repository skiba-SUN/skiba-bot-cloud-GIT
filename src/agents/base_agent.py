"""Base agent class for all AI agents"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from loguru import logger


class BaseAgent(ABC):
    """Abstract base class for AI agents"""

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize the base agent

        Args:
            name: Agent name
            description: Agent description
        """
        self.name = name
        self.description = description or f"Agent: {name}"
        self.tools: List[Any] = []
        self.conversation_history: List[Dict[str, str]] = []

        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    def run(self, query: str, **kwargs) -> str:
        """
        Run the agent with a query

        Args:
            query: User query
            **kwargs: Additional parameters

        Returns:
            Agent response
        """
        pass

    def add_tool(self, tool: Any):
        """
        Add a tool to the agent

        Args:
            tool: Tool to add
        """
        self.tools.append(tool)
        logger.info(f"Added tool to {self.name}: {tool}")

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info(f"Cleared conversation history for {self.name}")

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history

        Returns:
            List of conversation messages
        """
        return self.conversation_history

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (override in subclass for accurate counting)

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        # Simple approximation: ~4 characters per token
        return len(text) // 4
