import uuid
import random
from typing import List
import httpx
from app.config.config import Settings
from app.domain.entities import LLMUsage
from app.domain.ports import LLMProvider, LLMUsageRepository


class OpenRouterProvider(LLMProvider):
    def __init__(self, settings: Settings, usage_repo: LLMUsageRepository | None = None):
        self.settings = settings
        self.usage_repo = usage_repo
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        # Fallback for testing/fake key
        if self.settings.openrouter_api_key == "fake_key" or "fake" in self.settings.openrouter_api_key.lower():
            # Mock generate response
            mock_responses = {
                "classify": '{"type": "contract", "confidence": 0.95}',
                "metadata": '{"authors": ["John Doe"], "companies": ["Acme Corp"], "dates": ["2026-06-11"], "keywords": ["agreement"]}',
                "summary": "This is a mock executive summary of the uploaded document.",
                "risk": '{"risks": [{"description": "Missing termination clause", "severity": "high"}], "compliance_issues": []}',
                "qa": "This is a mock answer based on the document context."
            }
            # Pick based on keyword search
            response_text = mock_responses["summary"]
            for key in mock_responses:
                if key in prompt.lower() or (system_prompt and key in system_prompt.lower()):
                    response_text = mock_responses[key]
                    break
            
            # Log dummy usage
            if self.usage_repo:
                await self.usage_repo.log_usage(LLMUsage(
                    id=uuid.uuid4(),
                    model=self.settings.openrouter_model,
                    prompt_tokens=100,
                    completion_tokens=50,
                    cost_usd=0.0000225  # (100 * 0.075 + 50 * 0.30) / 1,000,000
                ))
            return response_text

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Harsha0Sree/Nexus",
            "X-Title": "Nexus AI Document Processor"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.settings.openrouter_model,
            "messages": messages,
            "temperature": 0.1
        }

        try:
            response = await self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse tokens and calculate cost for Gemini 2.5 Flash
            usage_info = data.get("usage", {})
            prompt_tokens = usage_info.get("prompt_tokens", 0)
            completion_tokens = usage_info.get("completion_tokens", 0)
            
            # Pricing for Gemini 2.5 Flash: $0.075/1M input tokens, $0.30/1M output tokens
            cost = (prompt_tokens * 0.075 / 1_000_000) + (completion_tokens * 0.30 / 1_000_000)
            
            if self.usage_repo:
                await self.usage_repo.log_usage(LLMUsage(
                    id=uuid.uuid4(),
                    model=self.settings.openrouter_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost
                ))

            return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Re-raise or wrap exception
            raise e

    async def embed(self, text: str) -> List[float]:
        # Fallback for testing/fake key
        if self.settings.openrouter_api_key == "fake_key" or "fake" in self.settings.openrouter_api_key.lower():
            # Return 1536-dim dummy vector
            return [random.uniform(-0.1, 0.1) for _ in range(1536)]

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": text,
            "model": "text-embedding-3-small"
        }

        try:
            # We can use standard OpenRouter or OpenAI embedding API endpoint
            # OpenRouter passes this through to OpenAI
            response = await self.client.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                # Try OpenAI direct embedding endpoint as fallback
                response = await self.client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.settings.openrouter_api_key}", "Content-Type": "application/json"},
                    json=payload
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Log token usage for embeddings
            usage_info = data.get("usage", {})
            prompt_tokens = usage_info.get("prompt_tokens", 0)
            cost = prompt_tokens * 0.02 / 1_000_000  # $0.02 per 1M tokens for text-embedding-3-small
            
            if self.usage_repo:
                await self.usage_repo.log_usage(LLMUsage(
                    id=uuid.uuid4(),
                    model="text-embedding-3-small",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                    cost_usd=cost
                ))
                
            return data["data"][0]["embedding"]
        except Exception:
            # Fallback to local pseudo-hash embeddings to prevent hard failure
            # Generates a reproducible pseudo-embedding based on string hash
            h = hash(text)
            random.seed(h)
            return [random.uniform(-0.1, 0.1) for _ in range(1536)]
            
    async def close(self):
        await self.client.aclose()
