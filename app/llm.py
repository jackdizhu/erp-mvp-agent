import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

from openai import OpenAI, APITimeoutError, RateLimitError, BadRequestError

from app.errors import (
    llm_timeout, llm_overload, llm_token_limit, llm_invalid_response
)

client_kwargs = {
    "api_key": os.getenv("OPENAI_API_KEY")
}
base_url = os.getenv("OPENAI_BASE_URL")
if base_url:
    client_kwargs["base_url"] = base_url
client = OpenAI(**client_kwargs)

SYSTEM_PROMPT = """你是ERP智能助手，可以帮助用户查询和管理ERP系统中的订单、库存和供应商信息。

你可以执行以下操作：
- 查询订单状态、批量查询订单
- 查询库存信息、查询供应商信息
- 创建销售订单或采购订单
- 修改订单、取消订单、删除订单
- 调整库存数量

对于修改、取消、删除等高风险操作，系统会要求用户确认后再执行。
请用简洁专业的中文回复用户。

系统已有以下参考数据：
- 供应商A: SUP-A, 供应商B: SUP-B
- 商品SKU: iPhone 15 = "iPhone-15", MacBook Pro 14 = "MacBook-Pro"
- 订单号示例: 123, 124, 125

当用户使用供应商名或商品名时，请自动映射到对应编号并调用工具。"""


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
