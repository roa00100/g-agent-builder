"""모델에 보내는 내용의 종류.

모델 요청의 내용 조각(나중)과 모델 명세의 input_kinds 가 이 정의 하나를 같이 쓴다.
"""

from typing import Literal

# 종류를 늘리면 infra 의 model_alias 테이블 검사 제약도 같이 고친다(마이그레이션).
InputKind = Literal["text", "image", "file"]
