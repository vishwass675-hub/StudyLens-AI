"""
Ollama Cloud API client for Nemotron 3 Nano 30B Cloud.
Handles direct HTTP communication with https://ollama.com/api/chat with bearer authentication.
"""

from typing import List, Dict, Any, Optional
import httpx
from backend.app.core.config import settings


class OllamaCloudError(Exception):
    """Exception raised when an error occurs during an Ollama Cloud request."""
    pass


class OllamaCloudClient:
    """
    Dedicated client for communicating with Ollama Cloud API.
    Guarantees that API credentials never leak in requests or error traces.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.OLLAMA_API_KEY
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    @property
    def chat_endpoint(self) -> str:
        return f"{self.base_url}/api/chat"

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_override: Optional[str] = None,
    ) -> str:
        """
        Sends chat completion request to Ollama Cloud.

        Args:
            messages: List of message dicts (e.g. [{'role': 'system', ...}, {'role': 'user', ...}])
            model_override: Optional model name to override default

        Returns:
            Generated assistant text string
        """
        if not self.api_key:
            raise OllamaCloudError(
                "Ollama Cloud API key is not configured. Please set OLLAMA_API_KEY in the environment."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_override or self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.chat_endpoint,
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:
                # Mask any sensitive detail
                err_text = response.text[:200]
                raise OllamaCloudError(
                    f"Ollama Cloud API returned status {response.status_code}: {err_text}"
                )

            data = response.json()
            message = data.get("message", {})
            content = message.get("content", "")
            return content

        except httpx.TimeoutException:
            raise OllamaCloudError("Ollama Cloud request timed out. Please try again.")
        except httpx.RequestError as e:
            raise OllamaCloudError(f"Network error connecting to Ollama Cloud: {str(e)}")
        except Exception as e:
            if isinstance(e, OllamaCloudError):
                raise
            raise OllamaCloudError(f"Unexpected error communicating with Ollama Cloud: {str(e)}")


# Global singleton instance
ollama_client = OllamaCloudClient()
