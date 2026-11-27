# agent-builder-core

에이전트 빌더의 커널 — 공통 계약 구조를 둔다. 사용자가 자기만의 에이전트를 조립해서, 필요한 업무 단계(workflow 의 특정 단계)에서 그 에이전트의 보조를 받는다.

core 는 특정 기술(DB·Redis·모델 공급자)을 모른다. 의존성은 Pydantic 뿐이고, 구현은 `agent-builder-runtime` 이 infra 의 기술 구성을 써서 채운다.
작업 규칙은 저장소 루트의 `AGENTS.md` 를 본다. `agent-handoff.md` 는 과거 다른 프로젝트의 경험을 정리한 참고 문서다.

| 모듈 | 내용 |
|---|---|
| `contracts/envelope.py` | `Envelope` — 모든 계약 모양의 부모. 모르는 필드 거부, 만든 뒤 불변 |
| `contracts/model/` | 모델 계약. 모델 요청 `ModelRequest`(메시지·생성 옵션·출력 모양·도구·추적, 버전 1), 내용 조각 `TextPart`·`ImagePart`·`FilePart`와 출처 `InlineSource`·`UrlSource`·`StoredSource`, 요청이 모델에 맞는지 보는 `check_inputs`. 모델 응답 `ModelResponse`(본문은 요청의 `Message`, 종료 사유 다섯 가지, 사용량·비용, 걸린 시간), 실패 예외 `ModelCallFailed`(종류·`retryable`), 원하는 모양으로 읽는 `parse_output`. 공급자 계약 `ModelProvider`(`complete(request, spec)`, 한 번만 보낸다)와 `UnknownProvider` |
| `model/` | 모델 호출 서비스 `ModelGateway` — 대응표 찾기, `check_inputs`, 저장된 파일 출처 막기(FileStore 전까지), 공급자 고르기, 보내기, 응답이 보낸 요청의 것인지 확인. 다시 보내지 않는다 그리고 `InputKind`(text·image·file), 모델 대응표 `ModelSpec`, 찾기·고치기 계약 `ModelCatalog`, 오류 `UnknownModel`·`DisabledModel`, 규칙 `resolve_model`(없거나 꺼진 이름은 오류). 구현은 runtime 의 `ModelCatalogRepository` |
| `workflow/` | workflow 정의 — 단계의 순서, 단계마다 입력·출력, 누가 하는가. 비어 있음 |
| `run/` | 실행 상태 — 지금 어느 단계인가, 단계별 결과, 멈췄다 이어 가기. 비어 있음 |
| `assist/` | AI 보조 단계 — 보조 프로필에 따라 제안을 만든다. 비어 있음 |

## 테스트

DB·Redis 없이 돈다. 설치는 저장소 루트 `AGENTS.md` 6절을 본다.

```powershell
..\.venv\Scripts\python -m pytest
```

`tests/test_package.py` 는 core 가 infra 나 기술 패키지를 import 하지 않는지도 확인한다.
