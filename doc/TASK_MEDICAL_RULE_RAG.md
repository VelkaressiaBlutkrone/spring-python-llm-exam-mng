# 병원규칙 RAG 벡터 검색 명세서

## 문제 정의

병원규칙 Q&A 챗봇이 LLM 일반 지식에만 의존하고 있어, 실제 병원 규칙 데이터를 DB에 저장하고 벡터 검색(RAG)을 통해 근거 기반 답변을 생성하도록 개선한다.

## 대상 사용자

- **병원 직원(의사·간호사)**: 병원 내부 규칙에 대해 질의

## 핵심 요구사항 (우선순위순)

1. [P0] `medical_rule` 테이블 신규 생성 (MySQL 원본 저장소)
   - `category`: 카테고리 (당직/근무, 물품/비품, 위생/감염 등)
   - `title`: 규칙 제목
   - `content`: 규칙 본문 (문서 단위, 크기 유동적)
   - `target`: 적용 대상
   - `start_date`: 시행 시작일
   - `end_date`: 시행 종료일
2. [P0] JSON 파일로 초기 데이터 import 기능
3. [P0] ChromaDB에 규칙 데이터 벡터 인덱싱 (검색 엔진 역할)
4. [P0] 병원규칙 Q&A 흐름 변경: 질문 → ChromaDB 벡터 검색 → 관련 규칙을 LLM 컨텍스트에 포함 → 답변 생성
5. [P1] MySQL(원본) ↔ ChromaDB(벡터) 이중 관리 구조

## 제약 조건 & 전제

- ChromaDB는 Python LLM 서버 venv에 이미 설치됨
- 기존 `/infer/rule` Python 엔드포인트를 수정하여 벡터 검색 컨텍스트 주입
- Spring Boot 측 `ChatController` / `ChatService`는 API 호출만 하므로 변경 최소화
- 프로젝트 코드 컨벤션(`.claude/rules/common-rule.md`) 준수

## 엣지 케이스 & 에러 시나리오

- 벡터 검색 결과가 0건일 때 → 기존처럼 일반 지식으로 답변 + "해당 병원 규칙을 확인해 주세요" 안내
- JSON import 시 중복 데이터 처리
- ChromaDB 인덱스와 MySQL 데이터 동기화

## 범위 밖 (명시적 제외)

- 규칙 데이터 CRUD 관리 화면 (Admin UI)
- 규칙 문서 자동 크롤링/수집
- 의학지식(질병 Q&A) 쪽 변경

## 수용 기준

- [ ] `medical_rule` 테이블 생성 및 JSON import로 데이터 적재
- [ ] ChromaDB에 규칙 데이터 벡터 인덱싱 완료
- [ ] 병원규칙 Q&A에서 질문 시 관련 규칙이 컨텍스트로 포함되어 답변 생성
- [ ] 벡터 검색 결과가 없을 때도 정상 응답
