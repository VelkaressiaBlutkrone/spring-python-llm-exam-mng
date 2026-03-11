# 컨트롤러 분리 명세서

## 문제 정의

하나의 컨트롤러와 하나의 화면에 혼재된 질병 Q&A / 의학지식·병원규칙 두 LLM 기능을 컨트롤러, 화면, 데이터 레이어 모두에서 분리하여 각각 독립적으로 운영한다.

## 대상 사용자

- **학습자(본인)**: 기능 분리 구조를 학습하기 위한 프로젝트

## 핵심 요구사항 (우선순위순)

1. [P0] `LlmController`를 `MedicalController`(`/medical/**`)와 `ChatController`(`/chat/**`)로 분리
2. [P0] 메인 허브 페이지 신규 생성 — "질병 Q&A" / "의학지식·병원규칙" 카드 2개로 각 페이지 진입
3. [P0] 질병 Q&A 페이지 — 기존 `index.html` UI 재활용, `MedicalController` 연결
4. [P0] 의학지식·병원규칙 페이지 — 채팅 메신저 스타일 UI 신규 작성, `ChatController` 연결
5. [P0] 기존 `chat_history` 테이블 → `medical_history`로 리네이밍 (질병 Q&A 전용)
6. [P0] 의학지식·병원규칙용 `chat_history` 테이블 신규 생성
7. [P1] Service, Repository, DTO, Entity도 각 도메인별로 분리

## 제약 조건 & 전제

- Python LLM 서버(`app.py`)는 이미 엔드포인트가 분리되어 있으므로 큰 변경 없음
- LLM 모델 및 RAG 데이터 소스는 현재 공유, 추후 필요 시 분리
- 프로젝트 코드 컨벤션(`.ai/rules/common-rule.md`) 준수

## 엣지 케이스 & 에러 시나리오

- 기존 `chat_history` → `medical_history` 마이그레이션 시 기존 데이터 처리 (마이그레이션 SQL 필요)

## 범위 밖 (명시적 제외)

- Python LLM 서버의 모델/RAG 분리
- 메인 페이지에 통계, 최근 대화 목록 등 부가 기능
- Spring Security 등 인증/권한 처리

## 수용 기준

- [ ] 메인 허브 페이지에서 두 기능 페이지로 각각 이동 가능
- [ ] 질병 Q&A 페이지가 `MedicalController` → Python LLM 서버로 정상 동작
- [ ] 의학지식·병원규칙 페이지가 `ChatController` → Python LLM 서버로 정상 동작
- [ ] 두 기능의 대화 이력이 각각 `medical_history`, `chat_history` 테이블에 독립 저장
- [ ] 기존 데이터 마이그레이션 SQL 제공
