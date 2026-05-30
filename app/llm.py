import os
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

from openai import OpenAI, APITimeoutError, RateLimitError, BadRequestError

from app.errors import (
    llm_timeout, llm_overload, llm_token_limit, llm_invalid_response
)
from app.prompt_config import build_system_prompt

SYSTEM_PROMPT = build_system_prompt()

client_kwargs = {
    "api_key": os.getenv("OPENAI_API_KEY")
}
base_url = os.getenv("OPENAI_BASE_URL")
if base_url:
    client_kwargs["base_url"] = base_url
client = OpenAI(**client_kwargs)


def call_llm(messages: list, tools: list = None) -> dict:
    try:
        kwargs = {
            "model": os.getenv("LLM_MODEL", "gpt-4o"),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        content = choice.message.content
        tool_calls = choice.message.tool_calls

        return {
            "finish_reason": finish_reason,
            "content": content,
            "tool_calls": tool_calls
        }

    except APITimeoutError:
        raise ValueError(llm_timeout())
    except RateLimitError:
        raise ValueError(llm_overload())
    except BadRequestError as e:
        if "token" in str(e).lower() or "length" in str(e).lower():
            raise ValueError(llm_token_limit(str(e)))
        raise ValueError(llm_invalid_response(str(e)))
    except Exception as e:
        raise ValueError(llm_invalid_response(str(e)))


def call_llm_stream(messages: list, tools: list = None, on_chunk: Callable[[str], None] = None) -> dict:
    try:
        kwargs = {
            "model": os.getenv("LLM_MODEL", "gpt-4o"),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = client.chat.completions.create(**kwargs)

        full_content = ""
        tool_calls = None

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                full_content += delta.content
                if on_chunk:
                    on_chunk(delta.content)

            if delta.tool_calls:
                if tool_calls is None:
                    tool_calls = []
                for tc in delta.tool_calls:
                    if tc.index is not None and tc.index < len(tool_calls):
                        existing = tool_calls[tc.index]
                        if tc.function and tc.function.arguments:
                            existing.function.arguments += tc.function.arguments
                    else:
                        tool_calls.append(tc)

        choice = chunk.choices[0] if chunk.choices else None
        finish_reason = choice.finish_reason if choice else "stop"

        return {
            "finish_reason": finish_reason,
            "content": full_content,
            "tool_calls": tool_calls
        }

    except APITimeoutError:
        raise ValueError(llm_timeout())
    except RateLimitError:
        raise ValueError(llm_overload())
    except BadRequestError as e:
        if "token" in str(e).lower() or "length" in str(e).lower():
            raise ValueError(llm_token_limit(str(e)))
        raise ValueError(llm_invalid_response(str(e)))
    except Exception as e:
        raise ValueError(llm_invalid_response(str(e)))
