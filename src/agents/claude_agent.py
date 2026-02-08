"""Claude-based AI agent implementation"""

from typing import Any, Dict, List, Optional
from anthropic import Anthropic
from loguru import logger

from .base_agent import BaseAgent
from ..config import get_settings


class ClaudeAgent(BaseAgent):
    """AI Agent powered by Anthropic Claude"""

    def __init__(
        self,
        name: str = "Claude Agent",
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize Claude agent

        Args:
            name: Agent name
            description: Agent description
            system_prompt: System prompt for the agent
        """
        super().__init__(name, description)

        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.anthropic_api_key)
        self.system_prompt = system_prompt or self._default_system_prompt()

        logger.info(f"Claude agent initialized with model: {self.settings.model_name}")

    def _default_system_prompt(self) -> str:
        """Default system prompt"""
        return """You are a helpful AI assistant powered by Claude.
You provide accurate, thoughtful, and well-reasoned responses.
When you're uncertain, you acknowledge it rather than making up information."""

    def run(
        self,
        query: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Run the agent with a query

        Args:
            query: User query
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Agent response
        """
        try:
            # Add query to history
            self.conversation_history.append({"role": "user", "content": query})

            # Log token usage for cost tracking
            input_tokens = self.count_tokens(query + self.system_prompt)
            logger.info(f"Input tokens (estimated): {input_tokens}")

            # Make API call
            response = self.client.messages.create(
                model=self.settings.model_name,
                max_tokens=max_tokens or self.settings.max_tokens,
                temperature=temperature or self.settings.temperature,
                system=self.system_prompt,
                messages=self.conversation_history,
            )

            # Extract response
            assistant_message = response.content[0].text

            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Log token usage
            logger.info(
                f"API call completed - "
                f"Input tokens: {response.usage.input_tokens}, "
                f"Output tokens: {response.usage.output_tokens}"
            )

            # Calculate cost (approximate for Sonnet 4.5)
            input_cost = (response.usage.input_tokens / 1_000_000) * 3.0
            output_cost = (response.usage.output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            logger.info(f"Estimated cost: ${total_cost:.6f}")

            return assistant_message

        except Exception as e:
            logger.error(f"Error in Claude agent: {str(e)}")
            raise

    def run_with_tools(self, query: str, tools: Optional[List[Dict]] = None) -> str:
        """
        Run agent with tool use capabilities

        Args:
            query: User query
            tools: List of tool definitions

        Returns:
            Agent response
        """
        # This is a placeholder for tool use implementation
        # Will be expanded based on specific tool requirements
        logger.info("Tool use requested - to be implemented")
        return self.run(query)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """
        Estimate API call cost

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost breakdown
        """
        # Claude Sonnet 4.5 pricing (as of 2025)
        input_cost_per_million = 3.0
        output_cost_per_million = 15.0

        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
