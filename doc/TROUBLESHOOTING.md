# 트러블슈팅 가이드

프로젝트 개발 중 발생한 주요 문제점과 해결 방법을 정리한 문서입니다.

---

## 목차

- [트러블슈팅 가이드](#트러블슈팅-가이드)
  - [목차](#목차)
  - [1. 의사 목록 진료 스케줄 미표시](#1-의사-목록-진료-스케줄-미표시)
    - [증상](#증상)
    - [원인](#원인)
    - [해결](#해결)
    - [교훈](#교훈)
  - [2. 복합 증상 질의 시 응답 지연](#2-복합-증상-질의-시-응답-지연)
    - [증상](#증상-1)
    - [원인](#원인-1)
    - [해결: SSE 스트리밍 + 프롬프트 최적화 (동시 적용)](#해결-sse-스트리밍--프롬프트-최적화-동시-적용)
    - [교훈](#교훈-1)
  - [3. AI 상담 응답 영역 빈칸 출력](#3-ai-상담-응답-영역-빈칸-출력)
    - [증상](#증상-2)
    - [원인](#원인-2)
    - [해결](#해결-1)
    - [교훈](#교훈-2)
  - [4. SSE 데이터 파싱 실패](#4-sse-데이터-파싱-실패)
    - [증상](#증상-3)
    - [원인](#원인-3)
    - [해결](#해결-2)
    - [교훈](#교훈-3)
  - [5. Chrome DevTools .well-known 404 오류](#5-chrome-devtools-well-known-404-오류)
    - [증상](#증상-4)
    - [원인](#원인-4)
    - [해결](#해결-3)
    - [교훈](#교훈-4)
  - [6. FULLTEXT 검색 키워드 미매칭](#6-fulltext-검색-키워드-미매칭)
    - [증상](#증상-5)
    - [원인](#원인-5)
    - [해결: RAG/벡터 검색 도입](#해결-rag벡터-검색-도입)
    - [교훈](#교훈-5)
  - [7. 로딩 위젯 동작 순서 문제](#7-로딩-위젯-동작-순서-문제)
    - [증상](#증상-6)
    - [원인](#원인-6)
    - [해결](#해결-4)
    - [변경 후 흐름](#변경-후-흐름)
    - [교훈](#교훈-6)
  - [8. DoctorScheduleDto 생성자 타입 불일치](#8-doctorscheduledto-생성자-타입-불일치)
    - [증상](#증상-7)
    - [원인](#원인-7)
    - [해결](#해결-5)
    - [교훈](#교훈-7)
  - [9. 추천 진료과 의사 0명 반환](#9-추천-진료과-의사-0명-반환)
    - [증상](#증상-8)
    - [원인](#원인-8)
    - [해결](#해결-6)
    - [교훈](#교훈-8)
  - [10. 스트리밍 응답에 중국어(CJK) 문자 혼입](#10-스트리밍-응답에-중국어cjk-문자-혼입)
    - [증상](#증상-9)
    - [원인](#원인-9)
    - [해결: 2중 방어](#해결-2중-방어)
    - [교훈](#교훈-9)
  - [11. Vector DB(ChromaDB) 조회 실패](#11-vector-dbchromadb-조회-실패)
    - [증상](#증상-10)
    - [원인 (복합적)](#원인-복합적)
    - [해결](#해결-7)
    - [개선된 로그](#개선된-로그)
    - [교훈](#교훈-10)
  - [12. MySQL 커넥션 풀 Startup Hang (aiomysql)](#12-mysql-커넥션-풀-startup-hang-aiomysql)
    - [증상](#증상-11)
    - [원인](#원인-10)
    - [해결](#해결-8)
    - [교훈](#교훈-11)
  - [13. ChromaDB Windows Segfault (PersistentClient)](#13-chromadb-windows-segfault-persistentclient)
    - [증상](#증상-12)
    - [원인](#원인-11)
    - [해결](#해결-9)
    - [교훈](#교훈-12)
  - [14. ChromaDB API 버전 불일치 (KeyError: '\_type')](#14-chromadb-api-버전-불일치-keyerror-_type)
    - [증상](#증상-13)
    - [원인](#원인-12)
    - [해결](#해결-10)
    - [교훈](#교훈-13)
  - [15. LLM 응답 중국어 구두점 반복 및 문장 잘림](#15-llm-응답-중국어-구두점-반복-및-문장-잘림)
    - [증상](#증상-14)
    - [원인](#원인-13)
    - [해결](#해결-11)
    - [교훈](#교훈-14)
  - [16. Windows localhost IPv6 해석으로 MySQL 연결 실패](#16-windows-localhost-ipv6-해석으로-mysql-연결-실패)
    - [증상](#증상-15)
    - [원인](#원인-14)
    - [해결](#해결-12)
    - [검증](#검증)
    - [교훈](#교훈-15)
  - [17. Docker Desktop WSL2 외부 IP 접속 불가](#17-docker-desktop-wsl2-외부-ip-접속-불가)
    - [증상](#증상-16)
    - [원인](#원인-15)
    - [해결](#해결-13)
    - [교훈](#교훈-16)
  - [18. Docker 데이터 C 드라이브 용량 부족](#18-docker-데이터-c-드라이브-용량-부족)
    - [증상](#증상-17)
    - [해결](#해결-14)
    - [교훈](#교훈-17)
  - [19. ChromaDB Docker 컨테이너 unhealthy](#19-chromadb-docker-컨테이너-unhealthy)
    - [증상](#증상-18)
    - [원인](#원인-16)
    - [해결](#해결-15)
    - [교훈](#교훈-18)
  - [20. MySQL llm-db InnoDB 데이터 손상](#20-mysql-llm-db-innodb-데이터-손상)
    - [증상](#증상-19)
    - [원인](#원인-17)
    - [해결](#해결-16)
    - [교훈](#교훈-19)
  - [21. docker compose down -v 후에도 볼륨 미삭제](#21-docker-compose-down--v-후에도-볼륨-미삭제)
    - [증상](#증상-20)
    - [해결](#해결-17)
  - [22. index\_medical\_data.py DuplicateIDError](#22-index_medical_datapy-duplicateiderror)
    - [증상](#증상-21)
    - [원인](#원인-18)
    - [해결](#해결-18)
  - [23. PowerShell에서 MySQL SQL 파일 리다이렉션 실패](#23-powershell에서-mysql-sql-파일-리다이렉션-실패)
    - [증상](#증상-22)
    - [해결](#해결-19)
  - [24. MySQL "Using a password on the command line" 경고](#24-mysql-using-a-password-on-the-command-line-경고)
    - [증상](#증상-23)
    - [해결](#해결-20)
  - [25. 병원 규칙 Q\&A 무조건 "등록되어 있지 않습니다" 응답](#25-병원-규칙-qa-무조건-등록되어-있지-않습니다-응답)
    - [증상](#증상-24)
    - [원인](#원인-19)
    - [해결](#해결-21)
  - [부록: 개발 환경 관련 이슈](#부록-개발-환경-관련-이슈)
    - [Windows CRLF + Tab 들여쓰기](#windows-crlf--tab-들여쓰기)
    - [.gitignore 누락](#gitignore-누락)

---

## 1. 의사 목록 진료 스케줄 미표시

### 증상

- `/api/llm/query/medical` 응답에서 의사 목록은 정상 반환되지만, 프론트엔드 테이블의 "진료 스케줄" 컬럼이 비어 있음

### 원인

- `MedicalLlmResponse`에서 `List<DoctorDto>`를 사용하고 있었음
- `DoctorDto`에는 `schedules` 필드가 없어 API 응답에 스케줄 데이터가 포함되지 않음

### 해결

- `DoctorDto` → `DoctorWithScheduleDto`로 변경 (스케줄 정보 포함)
- 전체 스택 일괄 수정:

| 파일                      | 변경                                                  |
| ------------------------- | ----------------------------------------------------- |
| `MedicalLlmResponse.java` | `List<DoctorDto>` → `List<DoctorWithScheduleDto>`     |
| `MedicalController.java`   | `findDoctors()` → `findDoctorsWithSchedule()`         |
| `MedicalIntegrationTest.java` | Mock 객체를 `DoctorWithScheduleDto`로 변경         |
| `index.html`              | `formatSchedules()` 함수 추가, 테이블에 스케줄 렌더링 |

### 교훈

- DTO 변경 시 Controller → Service → Test → Frontend 전체 경로를 확인할 것

---

## 2. 복합 증상 질의 시 응답 지연

### 증상

- 단순 질문(예: "두통")은 3~5초 내 응답
- 복합 질문(예: "무릎이 아프고 걸을 때 통증이 심하며 부종도 있습니다")은 15~30초 이상 소요
- 사용자가 응답이 없다고 판단하여 이탈

### 원인

1. **프롬프트 길이**: 의학 컨텍스트가 길어질수록 Ollama 추론 시간 증가
2. **동기식 응답**: 전체 응답이 완성될 때까지 사용자에게 아무것도 표시되지 않음

### 해결: SSE 스트리밍 + 프롬프트 최적화 (동시 적용)

**A. SSE 스트리밍 (체감 속도 개선)**

| 계층     | 구현                                                                           |
| -------- | ------------------------------------------------------------------------------ |
| Python   | `/infer/medical/stream` 엔드포인트, Ollama `stream:true` → `StreamingResponse` |
| Spring   | `Flux<String>` 반환, `TEXT_EVENT_STREAM_VALUE` produces                        |
| Frontend | `fetch` + `ReadableStream` + `data:` 파싱                                      |

**B. 프롬프트 최적화 (실제 속도 개선)**

- `medical_context_max_chars = 1500` 설정으로 컨텍스트 길이 제한
- 마지막 완전한 줄 기준으로 자르기 (문장 중간 잘림 방지)

### 교훈

- 체감 속도(스트리밍)와 실제 속도(프롬프트 최적화)를 동시에 개선하는 것이 효과적

---

## 3. AI 상담 응답 영역 빈칸 출력

### 증상

- 의사 목록과 추천 진료과는 정상 표시
- "AI 상담 응답" 카드 내용이 비어 있음

### 원인

1. SSE 스트리밍이 실패(네트워크 또는 서버 오류)했지만 **에러가 무시**됨
2. 스트리밍 실패 후 기존 API(`/query/medical`) 응답의 `generatedText`를 AI 응답 영역에 렌더링하는 로직이 없었음
3. `renderDoctorCards()`가 진료과/의사만 렌더링하고 AI 텍스트는 처리하지 않음

### 해결

```javascript
// 스트리밍 실패 시 기존 API 응답으로 폴백
if (!streamedText) {
  renderLlmResponse(data); // generatedText로 AI 응답 표시
}
```

- `renderLlmResponse()` 함수 추가: 추천 진료과 중복 텍스트 제거 후 AI 응답 렌더링
- `streamResponse()` catch 블록에서 에러를 상위로 전파하되, UI는 깨지지 않도록 처리

### 교훈

- 스트리밍은 항상 실패할 수 있으므로 **폴백 렌더링**이 필수
- "표시 안 됨" 문제는 대부분 렌더링 함수 호출 누락

---

## 4. SSE 데이터 파싱 실패

### 증상

- SSE 스트리밍 연결은 성공하지만 토큰이 화면에 표시되지 않음
- 콘솔에 JSON 파싱 에러 발생

### 원인

- SSE 표준: `data: {"token":"..."}`(data 뒤 공백)
- Spring MVC 프록시 경유 시: `data:{"token":"..."}`(공백 없음)
- 프론트엔드에서 `line.startsWith('data: ')`(공백 포함)로 파싱하여 불일치

### 해결

```javascript
// 변경 전 (공백 필수)
if (!line.startsWith('data: ')) continue;
const data = line.substring(6).trim();

// 변경 후 (공백 유무 모두 대응)
if (!line.startsWith('data:')) continue;
const data = line.substring(5).trim();
```

### 교훈

- SSE 파싱 시 `data:` 접두사만 확인하고 `.trim()`으로 공백 처리할 것
- 중간 프록시(Spring, Nginx 등)가 SSE 포맷을 변경할 수 있음

---

## 5. Chrome DevTools .well-known 404 오류

### 증상

- Spring Boot 로그에 `NoResourceFoundException` 발생:
  ```
  GET /.well-known/appspecific/com.chrome.devtools.json → 404
  ```

### 원인

- Chrome DevTools가 자동으로 요청하는 메타데이터 경로
- 애플리케이션과 무관한 브라우저 내부 요청

### 해결

- **수정 불필요** — 무해한 요청이며, 기능에 영향 없음
- 로그가 거슬리면 `application.yml`에서 해당 경로를 무시하도록 설정 가능:
  ```yaml
  spring:
    web:
      resources:
        add-mappings: false # 또는 특정 경로 필터링
  ```

### 교훈

- 404 로그가 모두 문제는 아님, 브라우저/도구의 자동 요청을 구분할 것

---

## 6. FULLTEXT 검색 키워드 미매칭

### 증상

- "머리가 아파요" 질문에 두통 관련 데이터가 검색되지 않음
- 동의어, 유사 표현에 대한 검색 품질 낮음

### 원인

- MySQL FULLTEXT(ngram)은 키워드 기반 → 의미적 유사도를 반영하지 못함
- `extract_keywords()`가 2글자 이상 단어만 추출 → 짧은 단어 누락

### 해결: RAG/벡터 검색 도입

- Ollama `nomic-embed-text` + ChromaDB로 의미 기반 벡터 검색 추가
- 하이브리드 검색: 벡터 검색 우선 → FULLTEXT 폴백

```
벡터 결과 >= 2건 → 벡터 결과만 사용
벡터 결과 < 2건  → FULLTEXT Q&A 검색 보완
벡터 결과 < 1건  → FULLTEXT 콘텐츠 검색 추가 보완
```

- 상세 내용: [TASK_RAG_VECTOR_SEARCH.md](TASK_RAG_VECTOR_SEARCH.md) 참고

### 교훈

- 키워드 검색과 벡터 검색을 조합(하이브리드)하면 각각의 약점을 보완할 수 있음
- 벡터 검색 실패 시 기존 검색으로 자동 폴백하여 안정성 확보

---

## 7. 로딩 위젯 동작 순서 문제

### 증상

1. 질문 제출 → 로딩 스피너 표시
2. SSE 스트리밍 시작 → 로딩 숨김, AI 텍스트 스트리밍
3. 스트리밍 완료 → **로딩이 다시 나타남** (의사 목록 API 호출 중)
4. 의사 목록 API 완료 → 로딩 숨김, 진료과/의사 표시

사용자 입장에서 "AI 응답이 끝났는데 왜 또 로딩이 나오지?" 라는 혼란 발생

### 원인

- SSE 스트리밍과 의사 목록 API 호출이 **순차 실행** (직렬)
- 스트리밍 완료 후 의사 목록 API를 호출하면서 로딩 스피너를 다시 활성화

### 해결

**A. 병렬 호출**: 스트리밍과 의사 목록 API를 동시에 시작

```javascript
const streamPromise = streamResponse(query);
const doctorPromise = fetchDoctorData(query);
const streamedText = await streamPromise;
const data = await doctorPromise;
```

**B. 로딩 1회만 표시**: 첫 토큰 도착 시 로딩 숨기고, 두 번째 로딩 제거

```javascript
if (firstToken) {
  firstToken = false;
  document.getElementById("loading").classList.remove("active");
  document.getElementById("llmCard").style.display = "block";
}
```

**C. 카드 순서 변경**: AI 응답 → 추천 진료과 → 의사 목록 (위에서 아래로 자연스럽게 채워짐)

### 변경 후 흐름

```
[상담하기] → 로딩 스피너
              ├─ SSE 스트리밍 시작 ──→ 첫 토큰 → 로딩 숨김 + AI 응답 실시간 표시
              └─ 의사목록 API 병렬 ──→ 완료 시 추천 진료과 + 의사 목록 추가
```

### 교훈

- 독립적인 API 호출은 병렬로 실행하여 총 대기 시간 단축
- 로딩 인디케이터는 "무엇을 기다리는지" 명확해야 함
- 부분 결과를 먼저 표시하면 체감 속도가 크게 개선됨

---

## 8. DoctorScheduleDto 생성자 타입 불일치

### 증상

- `MedicalIntegrationTest.java` 컴파일 오류:
  ```
  incompatible types: String cannot be converted to LocalTime
  ```

### 원인

- 테스트에서 `DoctorScheduleDto` 생성 시 시간 필드를 `String`("09:00")으로 전달
- 실제 DTO는 `LocalTime` 타입 사용

### 해결

```java
// 변경 전
new DoctorScheduleDto("MON", "09:00", "17:00", true)

// 변경 후
new DoctorScheduleDto("MON", LocalTime.of(9, 0), LocalTime.of(17, 0), true)
```

### 교훈

- DTO 필드 타입 변경 시 테스트 코드도 반드시 함께 수정
- `LocalTime` vs `String` 같은 시간 표현 타입은 프론트엔드 직렬화 형식도 확인할 것

---

## 9. 추천 진료과 의사 0명 반환

### 증상

- LLM이 "호흡기내과"를 추천했지만 의사 목록이 비어 있음
- 에러는 발생하지 않고 정상 응답이지만 `doctors: []`

### 원인

- 시드 데이터에 등록된 진료과: 정형외과, 신경과, 내과, 피부과
- LLM이 추천한 "호흡기내과"는 시드 데이터에 없음
- `findDoctorsWithSchedule("호흡기내과")` → 0건 조회는 정상 동작

### 해결

- 현 단계에서는 **정상 동작** (데이터 부재)
- 운영 환경에서는 실제 의사 데이터를 등록하면 해결됨
- 프론트엔드에서 의사 0명일 때 "해당 진료과 의사 정보가 없습니다" 안내 표시

### 교훈

- 시드 데이터 범위와 LLM 응답 범위가 일치하지 않을 수 있음
- 데이터 없는 경우에 대한 UI 안내 메시지 필요

---

## 10. 스트리밍 응답에 중국어(CJK) 문자 혼입

### 증상

- SSE 스트리밍으로 AI 응답을 실시간 수신할 때 한국어 사이에 중국어 문자가 섞여서 출력됨
- 비스트리밍(`/infer/medical`) 응답에서는 중국어가 제거되지만, 스트리밍에서는 그대로 노출

### 원인

1. **`response_cleaner`가 스트리밍에 미적용**: 비스트리밍 응답은 `clean_llm_response()`로 후처리하여 CJK 문자를 제거하지만, 스트리밍은 토큰을 그대로 전달
2. **gemma3:4b 모델 특성**: 한국어 프롬프트에도 중국어 문자를 간헐적으로 생성 (multilingual 모델 특성)
3. **시스템 프롬프트 미흡**: "한국어로만 답변" 지시가 모델에 충분히 전달되지 않음

### 해결: 2중 방어

**A. 스트리밍 토큰 실시간 필터링**

```python
# app.py - generate_sse() 내부
raw_token = chunk.get("message", {}).get("content", "")
if raw_token:
    token = NON_KOREAN_CJK_PATTERN.sub("", raw_token)
    if token:
        data = json.dumps({"token": token}, ensure_ascii=False)
        yield f"data: {data}\n\n"
```

**B. 시스템 프롬프트 강화**

- 영문 지시 추가: `"You MUST respond ONLY in Korean. NEVER use Chinese or Japanese."`
- 한자 명시 금지: `"한자(漢字)를 사용하지 마세요. 모든 내용을 한글로 작성하세요."`
- 중복 프롬프트를 `MEDICAL_SYSTEM_PROMPT` 상수로 추출하여 일관성 확보

### 교훈

- LLM 출력 언어 제어는 프롬프트만으로 100% 보장되지 않음 → **후처리 필터링 필수**
- 스트리밍과 비스트리밍 경로의 후처리 로직을 동일하게 유지할 것
- multilingual 모델 사용 시 원하지 않는 언어 혼입은 예상해야 함

---

## 11. Vector DB(ChromaDB) 조회 실패

### 증상

- 의학 질의 시 벡터 검색이 동작하지 않고 FULLTEXT 검색으로만 폴백됨
- Python 서버 로그에 `Vector search failed` 경고 또는 `Vector store is empty` 메시지

### 원인 (복합적)

| 로그 메시지                                | 원인                                           | 빈도      |
| ------------------------------------------ | ---------------------------------------------- | --------- |
| `Vector store is empty`                    | `index_medical_data.py` 미실행 (인덱싱 안 됨)  | 가장 흔함 |
| `ConnectionError` / `ConnectError`         | Ollama 서버 미실행 또는 임베딩 모델 미설치     | 흔함      |
| `Vector search dependencies not available` | `chromadb` 패키지 미설치                       | 초기 설정 |
| `ChromaDB initialization failed`           | `chroma_data/` 경로 권한 문제 또는 디스크 부족 | 드묾      |

### 해결

**1단계: 사전 준비**

```bash
# Ollama 임베딩 모델 다운로드
ollama pull nomic-embed-text

# Python 의존성 설치
cd python-llm
pip install -r requirements.txt
```

**2단계: 데이터 인덱싱**

```bash
python index_medical_data.py
```

성공 시 출력:

```
=== Indexing complete: 230 total documents in vector store ===
```

**3단계: 서버 시작 로그 확인**

```bash
uvicorn app:app --port 8000
```

정상:

```
ChromaDB ready: 230 documents indexed
```

실패:

```
ChromaDB initialization failed (vector search disabled): ...
```

**4단계: 벡터 검색 비활성화 (임시)**

```bash
USE_VECTOR_SEARCH=False uvicorn app:app --port 8000
```

### 개선된 로그

기존에는 `Vector search failed` 한 줄만 출력되었으나, 다음과 같이 상세화:

- 빈 벡터 스토어일 때 `index_medical_data.py` 실행 안내 + `ollama pull` 안내 포함
- 예외 타입(`ImportError`, `ConnectionError` 등)을 구분하여 원인 파악 용이

### 교훈

- 벡터 검색은 **인덱싱 선행 작업**이 필요하므로 서버 시작 시 상태를 로그로 알려야 함
- 벡터 검색 실패는 서비스 중단이 아닌 **graceful degradation** (FULLTEXT 폴백)으로 처리
- 설정 플래그(`use_vector_search`)로 즉시 비활성화 가능하게 하여 운영 안정성 확보

---

## 12. MySQL 커넥션 풀 Startup Hang (aiomysql)

### 증상

- Python FastAPI 서버 시작 시 42초 이상 hang 발생
- `lifespan` 이벤트에서 MySQL 커넥션 풀 생성 시 블로킹

### 원인

- `aiomysql.create_pool(minsize=2)` 설정으로 서버 시작 시 즉시 2개의 커넥션을 생성하려 함
- Docker MySQL이 완전히 준비되기 전에 연결 시도 → 타임아웃 대기

### 해결

```python
# 변경 전
_pool = await aiomysql.create_pool(..., minsize=2, maxsize=10)

# 변경 후: lazy init (첫 요청 시 커넥션 생성)
_pool = await aiomysql.create_pool(..., minsize=0, maxsize=10, connect_timeout=10)
```

- `minsize=0`: 시작 시 커넥션을 미리 만들지 않음
- `connect_timeout=10`: 무한 대기 방지

### 교훈

- Docker 환경에서는 DB가 healthy 상태여도 실제 연결 가능까지 시간차가 있음
- 서버 시작 시 DB 커넥션을 lazy하게 생성하면 기동 속도 개선

---

## 13. ChromaDB Windows Segfault (PersistentClient)

### 증상

- `python index_medical_data.py` 실행 시 `exit code 139` (segfault) 발생
- Windows 환경에서 ChromaDB `PersistentClient.upsert()` 호출 시 크래시

### 원인

- ChromaDB의 `PersistentClient`가 Windows에서 SQLite/hnswlib 네이티브 라이브러리 충돌
- 특히 대량 문서 upsert 시 메모리 관련 segfault 발생

### 해결

- ChromaDB를 Docker 컨테이너로 분리하고 `HttpClient`로 전환

```yaml
# docker-compose.yml
chromadb:
  image: chromadb/chroma:1.5.4
  ports:
    - "8100:8000"
```

```python
# vector_store.py
# 변경 전
_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

# 변경 후
_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
```

### 교훈

- ChromaDB PersistentClient는 Linux에서는 안정적이나 Windows에서 segfault 가능성 있음
- Docker HttpClient 방식이 플랫폼 독립적이고 안정적

---

## 14. ChromaDB API 버전 불일치 (KeyError: '\_type')

### 증상

- ChromaDB HttpClient 연결 시 `KeyError('_type')` 에러 발생
- 인덱싱/검색 모두 실패

### 원인

- Python `chromadb` 패키지 버전(1.5.4)과 Docker 이미지 버전(0.6.3) 불일치
- API 스키마가 다르기 때문에 응답 파싱 실패

### 해결

- Docker 이미지 버전을 Python 패키지와 일치시킴

```yaml
# docker-compose.yml
chromadb:
  image: chromadb/chroma:1.5.4 # python chromadb==1.5.4 와 동일 버전
```

### 교훈

- ChromaDB 클라이언트와 서버 버전은 반드시 일치시켜야 함
- `pip show chromadb`로 클라이언트 버전 확인 후 Docker 이미지 태그 맞출 것

---

## 15. LLM 응답 중국어 구두점 반복 및 문장 잘림

### 증상

- 의학 질의 응답에 `，。，。` 같은 중국어 구두점이 반복적으로 붙음
- 원래 문장이 잘려서 완전한 문장으로 출력되지 않음

### 원인

1. **구두점 반복**: qwen2.5:7b 모델이 중국어 구두점 패턴에 빠져 무한 반복 생성
2. **문장 잘림**: `max_length` 기본값이 100으로 너무 낮아 한국어 응답이 중간에 잘림

### 해결

**A. Stop sequences 추가**

```python
# 중국어 구두점 반복 패턴 감지 시 생성 중단
stop_sequences = ["，。，", "。，。"]
```

**B. response_cleaner 강화**

```python
# 중국어 구두점 연속 2개 이상 제거 (CJK 제거 전에 수행)
cleaned = re.sub(r"[，。、；：！？]{2,}", "", cleaned)
```

**C. max_length 기본값 증가**

```python
# schemas.py
max_length: int = Field(default=512, ...)  # 100 → 512
```

**D. 불완전 문장 마무리 기준 완화**

```python
# response_cleaner.py - _trim_incomplete_ending()
# 한국어 종결어미 패턴: 다, 요, 음, 니 등
# 완성 문장 비율 임계값: 70% → 50%
```

### 교훈

- multilingual 모델은 원치 않는 언어의 구두점도 생성할 수 있음 → stop sequences로 조기 중단
- 한국어는 영어보다 토큰 효율이 낮아 max_length를 넉넉하게 설정해야 함

---

## 16. Windows localhost IPv6 해석으로 MySQL 연결 실패

### 증상

- Python 서버에서 MySQL 연결 시 `OperationalError(2003, "Can't connect to MySQL server on 'localhost'")` 발생
- Docker MySQL 컨테이너는 healthy 상태이고 `docker exec`로는 정상 접속 가능

### 원인

- Windows에서 `localhost`가 IPv6 `::1`로 해석됨
- Docker는 IPv4 `0.0.0.0:3307`으로만 포트 바인딩
- `aiomysql`이 `::1:3307`로 연결 시도 → 타임아웃

### 해결

```python
# config.py
# 변경 전
mysql_host: str = Field(default="localhost", ...)

# 변경 후
mysql_host: str = Field(default="127.0.0.1", ...)
```

### 검증

```python
# localhost → 실패
await aiomysql.create_pool(host='localhost', port=3307, ...)  # TimeoutError

# 127.0.0.1 → 성공
await aiomysql.create_pool(host='127.0.0.1', port=3307, ...)  # OK
```

### 교훈

- Windows에서 Docker 컨테이너에 연결 시 `localhost` 대신 `127.0.0.1`을 명시적으로 사용
- IPv6/IPv4 듀얼 스택 환경에서 `localhost` 해석은 OS마다 다를 수 있음

---

## 17. Docker Desktop WSL2 외부 IP 접속 불가

### 증상

- `docker compose up` 후 `localhost:8080`은 정상 접속
- 같은 PC에서 LAN IP(`192.168.0.73:8080`)로 접속하면 타임아웃
- 다른 기기에서 `192.168.0.73:8080`은 정상 접속 가능

### 원인

- Docker Desktop WSL2 백엔드의 알려진 제한사항
- WSL2는 localhost 포트 포워딩만 지원하며, 호스트의 LAN IP를 통한 루프백 접속은 지원하지 않음
- `netsh interface portproxy`도 WSL2 환경에서는 동작하지 않음

### 해결

**방법 1: 같은 PC에서는 localhost 사용**

- 이 PC: `http://localhost:8080/`
- 다른 기기: `http://192.168.0.73:8080/`

**방법 2: Docker Desktop Hyper-V 백엔드 전환**

- Docker Desktop → Settings → General → "Use the WSL 2 based engine" 체크 해제
- Hyper-V 모드에서는 LAN IP 접속 가능

**방법 3: Windows 방화벽 포트 허용 (외부 기기 접속용)**

```powershell
# 관리자 PowerShell
netsh advfirewall firewall add rule name="Docker-8080" dir=in action=allow protocol=TCP localport=8080
```

### 교훈

- Docker Desktop WSL2는 localhost 전용, 외부 접속은 방화벽 규칙 필요
- 같은 PC에서 자기 LAN IP로 접속이 안 되는 것은 WSL2의 네트워킹 한계
- 외부 기기 접속이 목적이라면 방화벽 허용만으로 충분

---

## 18. Docker 데이터 C 드라이브 용량 부족

### 증상

- Docker 이미지/컨테이너가 C 드라이브에 저장되어 디스크 용량 부족
- `C:\Users\<user>\AppData\Local\Docker\wsl\` 경로에 약 33GB 사용

### 해결

- Docker Desktop → Settings → Resources → Advanced → **Disk image location**
- 경로를 `D:\DockerData` 등으로 변경 → Apply & Restart
- Docker Desktop이 자동으로 기존 데이터를 새 경로로 이동

### 교훈

- Docker Desktop 설치 후 초기에 데이터 경로를 여유 있는 드라이브로 설정하는 것을 권장
- 수동 WSL export/import 방식보다 Docker Desktop 설정 변경이 안전하고 간편

---

## 19. ChromaDB Docker 컨테이너 unhealthy

### 증상

- `docker compose up -d` 시 `container llm-chromadb is unhealthy` 오류
- ChromaDB 의존 서비스(python-llm 등)가 기동되지 않음

### 원인

- ChromaDB Docker 이미지에 `curl`이 포함되지 않은 경우 healthcheck 실패
- ChromaDB 기동에 60초 이상 소요되는데 healthcheck가 너무 빨리 시작됨

### 해결

- `docker-compose.yml`에서 healthcheck를 Python 기반으로 변경하고 `start_period` 추가

```yaml
chromadb:
  healthcheck:
    test:
      [
        "CMD",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v2/heartbeat', timeout=5)",
      ]
    interval: 15s
    timeout: 10s
    retries: 10
    start_period: 60s
```

### 교훈

- curl 미포함 이미지는 Python(ChromaDB 기반)으로 heartbeat 확인
- `start_period`로 초기 기동 시간 여유 확보

---

## 20. MySQL llm-db InnoDB 데이터 손상

### 증상

- `docker logs llm-db`에 `[ERROR] [MY-012960] [InnoDB] Cannot create redo log files because data files are corrupt` 오류

### 원인

- MySQL 초기화 중 컨테이너가 비정상 종료
- redo log 파일 손상으로 InnoDB가 기동 불가

### 해결

1. `docker compose down -v` 후 `docker compose up -d`
2. 볼륨이 남아 있으면 `docker volume rm spring_llm_sample_mng_llm_mysql_data` 수동 삭제
3. [DATA_RESTORE_GUIDE.md](DATA_RESTORE_GUIDE.md) 참고하여 데이터 재적재

### 교훈

- MySQL 컨테이너는 `docker compose down`으로 정상 종료할 것

---

## 21. docker compose down -v 후에도 볼륨 미삭제

### 증상

- `docker compose down -v` 실행 후에도 데이터 손상 오류가 반복됨

### 해결

1. `docker volume ls`로 볼륨 확인
2. `docker volume rm <볼륨명>` 수동 삭제
3. Docker Desktop 재시작 또는 WSL2 사용 시 `wsl --shutdown` 후 재실행

---

## 22. index_medical_data.py DuplicateIDError

### 증상

- `chromadb.errors.DuplicateIDError: Expected IDs to be unique, found duplicates of: content_xxx_chunk_0`

### 원인

- `medical_content`에서 `c_id`가 여러 행에서 중복
- 청크 ID `content_{c_id}_chunk_{i}`가 동일하게 생성됨

### 해결

- `index_medical_data.py`에서 청크 ID를 `row['id']`(PK) 기반으로 변경
- `fetch_medical_content` SELECT에 `id` 컬럼 추가

---

## 23. PowerShell에서 MySQL SQL 파일 리다이렉션 실패

### 증상

- `docker exec ... < scripts/medical-tables.sql` 실행 시 `ParserError: The '<' operator is reserved for future use`

### 해결

```powershell
Get-Content scripts/medical-tables.sql -Raw | docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db
```

---

## 24. MySQL "Using a password on the command line" 경고

### 증상

- `mysql: [Warning] Using a password on the command line interface can be insecure.` 출력

### 해결

- 오류가 아님. 경고만 출력되며 SQL 실행은 정상 완료됨

---

## 25. 병원 규칙 Q&A 무조건 "등록되어 있지 않습니다" 응답

### 증상

- 병원 규칙 질의 시 유사 내용이 있어도 LLM 추론 없이 해당 안내 메시지만 출력

### 원인

- ChromaDB rule 컬렉션이 비어 있으면 `rule_context`가 빈 문자열
- `app.py`에서 컨텍스트 없으면 LLM 호출 없이 바로 반환

### 해결

- `rule_context_service.py`에 MySQL `medical_rule` 테이블 폴백 검색 추가

---

## 부록: 개발 환경 관련 이슈

### Windows CRLF + Tab 들여쓰기

- 프로젝트 파일이 CRLF 줄바꿈 + Tab 들여쓰기 사용
- 코드 편집 도구에서 공백/탭 혼용 시 diff가 깨지거나 Edit 실패
- `cat -A` 명령으로 실제 들여쓰기 문자(탭 `^I` vs 공백)를 확인 후 편집

### .gitignore 누락

- `python-llm/chroma_data/` (ChromaDB 데이터)와 `__pycache__/` 가 .gitignore에 없어 불필요한 파일이 추적됨
- `.gitignore`에 추가하여 해결:

  ```
  python-llm/chroma_data/
  __pycache__/
  *.pyc
  ```
