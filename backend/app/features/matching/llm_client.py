import asyncio
from dataclasses import dataclass

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.2-3b-preview",
]


@dataclass
class LLMCompletionResult:
    content: str
    provider: str
    model: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None
    http_status: int | None = None
    prompt_preview: str | None = None


def _preview_text(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text)} chars total]"


def _log_llm_exchange(
    *,
    provider: str,
    model: str | None,
    prompt: str,
    system_prompt: str,
    result: LLMCompletionResult,
) -> None:
    if not settings.LLM_LOG_RESPONSES:
        return

    logger.info(
        "llm.exchange",
        provider=provider,
        model=model,
        skipped=result.skipped,
        skip_reason=result.skip_reason,
        error=result.error,
        http_status=result.http_status,
        system_prompt_preview=_preview_text(system_prompt),
        prompt_preview=_preview_text(prompt),
        response_preview=_preview_text(result.content) if result.content else None,
        response_length=len(result.content),
    )


async def generate_chat_completion(
    prompt: str,
    system_prompt: str = "You are an expert project matching assistant.",
    *,
    force: bool = False,
) -> LLMCompletionResult:
    """
    Generate chat completion from the configured LLM provider.
    When LLM_ENABLED is false (default), returns an empty skipped result
    unless force=True.
    """
    provider = settings.LLM_PROVIDER
    prompt_preview = _preview_text(prompt)

    if not settings.LLM_ENABLED and not force:
        result = LLMCompletionResult(
            content="",
            provider=provider,
            skipped=True,
            skip_reason=(
                "LLM_ENABLED is false. Set LLM_ENABLED=true in .env after testing "
                "with POST /api/matching/llm-preview."
            ),
            prompt_preview=prompt_preview,
        )
        _log_llm_exchange(
            provider=provider,
            model=None,
            prompt=prompt,
            system_prompt=system_prompt,
            result=result,
        )
        return result

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    if provider == "groq":
        result = await _call_groq(messages, prompt_preview)
    elif provider == "gemini":
        result = await _call_gemini(prompt, system_prompt, prompt_preview)
    elif provider == "openai":
        result = await _call_openai(messages, prompt_preview)
    else:
        result = await _call_ollama(messages, prompt_preview)

    _log_llm_exchange(
        provider=provider,
        model=result.model,
        prompt=prompt,
        system_prompt=system_prompt,
        result=result,
    )
    return result


async def _call_groq(
    messages: list[dict[str, str]], prompt_preview: str
) -> LLMCompletionResult:
    api_keys = [k.strip() for k in settings.GROQ_API_KEY.split(",") if k.strip()]
    if not api_keys:
        return LLMCompletionResult(
            content="",
            provider="groq",
            skipped=True,
            skip_reason="No GROQ_API_KEY configured.",
            prompt_preview=prompt_preview,
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    models: list[str] = []
    if settings.GROQ_MODEL:
        models.append(settings.GROQ_MODEL)
    for model_name in GROQ_MODELS:
        if model_name not in models:
            models.append(model_name)

    for idx, model in enumerate(models):
        for k_idx, api_key in enumerate(api_keys):
            logger.info(
                "Attempting LLM generation on Groq",
                model=model,
                key_index=k_idx + 1,
                attempt=idx * len(api_keys) + k_idx + 1,
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
            }

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        return LLMCompletionResult(
                            content=data["choices"][0]["message"]["content"],
                            provider="groq",
                            model=model,
                            http_status=200,
                            prompt_preview=prompt_preview,
                        )

                    if response.status_code == 429:
                        logger.warn(
                            "Groq rate limit reached (429)",
                            model=model,
                            key_index=k_idx + 1,
                        )
                        continue

                    logger.warn(
                        "Groq model returned error status",
                        model=model,
                        status=response.status_code,
                        body=response.text[:300],
                    )
            except Exception as e:
                logger.error(
                    "Exception during Groq request execution",
                    model=model,
                    error=str(e),
                )
                continue

    logger.warn("All Groq keys and models exhausted. Backing off for 6 seconds...")
    await asyncio.sleep(6.0)
    try:
        headers = {
            "Authorization": f"Bearer {api_keys[0]}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": models[0],
            "messages": messages,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return LLMCompletionResult(
                    content=data["choices"][0]["message"]["content"],
                    provider="groq",
                    model=models[0],
                    http_status=200,
                    prompt_preview=prompt_preview,
                )
            return LLMCompletionResult(
                content="",
                provider="groq",
                model=models[0],
                error=response.text[:500],
                http_status=response.status_code,
                prompt_preview=prompt_preview,
            )
    except Exception as e:
        return LLMCompletionResult(
            content="",
            provider="groq",
            model=models[0] if models else None,
            error=str(e) or type(e).__name__,
            prompt_preview=prompt_preview,
        )


async def _call_gemini(
    prompt: str, system_prompt: str, prompt_preview: str
) -> LLMCompletionResult:
    if not settings.GEMINI_API_KEY:
        return LLMCompletionResult(
            content="",
            provider="gemini",
            skipped=True,
            skip_reason="GEMINI_API_KEY is not configured.",
            prompt_preview=prompt_preview,
        )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"System Instruction: {system_prompt}\n\n"
                            f"User Input: {prompt}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return LLMCompletionResult(
                    content=data["candidates"][0]["content"]["parts"][0]["text"],
                    provider="gemini",
                    model="gemini-1.5-flash",
                    http_status=200,
                    prompt_preview=prompt_preview,
                )
            return LLMCompletionResult(
                content="",
                provider="gemini",
                model="gemini-1.5-flash",
                error=response.text[:500],
                http_status=response.status_code,
                prompt_preview=prompt_preview,
            )
    except Exception as e:
        return LLMCompletionResult(
            content="",
            provider="gemini",
            model="gemini-1.5-flash",
            error=str(e) or type(e).__name__,
            prompt_preview=prompt_preview,
        )


async def _call_ollama(
    messages: list[dict[str, str]], prompt_preview: str
) -> LLMCompletionResult:
    model = settings.OLLAMA_MODEL or "qwen2.5:7b"
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                return LLMCompletionResult(
                    content="",
                    provider="ollama",
                    model=model,
                    error=response.text[:500],
                    http_status=response.status_code,
                    prompt_preview=prompt_preview,
                )

            data = response.json()
            return LLMCompletionResult(
                content=data["choices"][0]["message"]["content"],
                provider="ollama",
                model=model,
                http_status=200,
                prompt_preview=prompt_preview,
            )
    except Exception as e:
        return LLMCompletionResult(
            content="",
            provider="ollama",
            model=model,
            error=str(e) or type(e).__name__,
            prompt_preview=prompt_preview,
        )


async def _call_openai(
    messages: list[dict[str, str]], prompt_preview: str
) -> LLMCompletionResult:
    if not settings.OPENAI_API_KEY:
        return LLMCompletionResult(
            content="",
            provider="openai",
            skipped=True,
            skip_reason="OPENAI_API_KEY is not configured.",
            prompt_preview=prompt_preview,
        )

    model = settings.OPENAI_MODEL or "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                return LLMCompletionResult(
                    content="",
                    provider="openai",
                    model=model,
                    error=response.text[:500],
                    http_status=response.status_code,
                    prompt_preview=prompt_preview,
                )

            data = response.json()
            return LLMCompletionResult(
                content=data["choices"][0]["message"]["content"],
                provider="openai",
                model=model,
                http_status=200,
                prompt_preview=prompt_preview,
            )
    except Exception as e:
        return LLMCompletionResult(
            content="",
            provider="openai",
            model=model,
            error=str(e) or type(e).__name__,
            prompt_preview=prompt_preview,
        )
