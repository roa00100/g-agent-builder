"""OpenRouter 와의 연결점.

openai SDK 클라이언트를 OpenRouter 주소로 두고, 보내고 받는다.
여기는 라이브러리를 부르는 데까지다. 본문을 어떻게 만들고 읽을지,
실패를 무엇으로 볼지는 runtime 의 OpenRouterAdapter 가 정한다.
그래서 core 의 계약 말(FailureKind 등)을 쓰지 않는다.
"""

from typing import Any, Literal

import httpx
import openai
from openai import OpenAI

# OpenRouter 의 OpenAI 호환 API 주소.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterCallError(Exception):
    """보냈지만 응답 본문을 받지 못했다. 기술의 말로만 알린다.

    reason:
      timeout     정해 둔 시간 안에 답이 없었다
      connection  붙지 못했다
      http        HTTP 오류 상태로 답했다 — status_code 와 body 가 있다
    """

    def __init__(
        self,
        reason: Literal["timeout", "connection", "http"],
        detail: str,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(f"[{reason}] {detail}")
        self.reason = reason
        self.detail = detail
        self.status_code = status_code
        self.body = body


class OpenRouterClient:
    """클라이언트를 만드는 것만으로는 OpenRouter 에 붙지 않는다."""

    def __init__(
        self,
        api_key: str,
        base_url: str = OPENROUTER_BASE_URL,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            # SDK 는 기본으로 실패를 두 번 더 보낸다. 끈다 — 다시 보낼지는 보조 고리의
            # 런타임이 정한다(T3). 여기서 몰래 다시 보내면 횟수·비용 한도가 어긋난다.
            max_retries=0,
            # 테스트에서 가짜 전송(httpx.MockTransport)을 끼울 때만 쓴다.
            http_client=http_client,
        )

    def chat(self, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        """chat completions 로 한 번 보내고 응답 본문을 dict 로 돌려준다.

        timeout_seconds: 이번 호출을 기다릴 시간. 공급자 프로필의 기본값이나
        모델별 덮어쓰기를 부르는 쪽(runtime)이 정해 넘긴다.

        SDK 가 모르는 필드(usage.cost 등)도 남는다.
        HTTP 200 인데 본문에 오류가 든 경우도 가르지 않고 그대로 돌려준다 —
        읽는 쪽(runtime)이 판단한다.
        """
        try:
            completion = self.client.chat.completions.create(
                **payload, timeout=timeout_seconds
            )
        except openai.APITimeoutError as error:
            raise OpenRouterCallError("timeout", str(error)) from error
        except openai.APIConnectionError as error:
            raise OpenRouterCallError("connection", str(error)) from error
        except openai.APIStatusError as error:
            raise OpenRouterCallError(
                "http", str(error), status_code=error.status_code, body=error.body
            ) from error
        return completion.model_dump()

    def ping(self) -> bool:
        """모델 목록을 받아 보면 True. 붙지 못하면 False 가 아니라 예외가 난다."""
        self.client.models.list()
        return True

    def close(self) -> None:
        self.client.close()
