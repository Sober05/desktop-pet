"""DeepSeek API client (OpenAI-compatible)."""
from openai import OpenAI, APITimeoutError, APIConnectionError
from config_mgr import get_api_key, get_model

TIMEOUT_SECONDS = 15


class AIClient:
    def __init__(self):
        self.api_key = get_api_key()
        self.model = get_model()
        self.base_url = "https://api.deepseek.com"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=TIMEOUT_SECONDS,
                max_retries=1,
            )
        return self._client

    def chat(self, messages, on_chunk=None):
        full = []
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=1024,
                temperature=0.7,
                timeout=TIMEOUT_SECONDS,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full.append(delta.content)
                    if on_chunk:
                        on_chunk(delta.content)
        except APITimeoutError:
            msg = "（网络不太好，超时了喵…待会再试试？）"
            full = [msg]
            if on_chunk:
                on_chunk(msg)
        except APIConnectionError:
            msg = "（连不上服务器喵…检查下网络？）"
            full = [msg]
            if on_chunk:
                on_chunk(msg)
        except Exception as e:
            msg = f"（出错了：{e}）"
            full = [msg]
            if on_chunk:
                on_chunk(msg)
        return "".join(full)

    def chat_sync(self, messages):
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                timeout=TIMEOUT_SECONDS,
            )
            return resp.choices[0].message.content
        except APITimeoutError:
            return "（网络超时了喵…待会再试试？）"
        except APIConnectionError:
            return "（连不上服务器喵…检查下网络？）"
        except Exception as e:
            return f"（API 错误：{e}）"
