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

| 파일 | 변경 |
|------|------|
| `MedicalLlmResponse.java` | `List<DoctorDto>` → `List<DoctorWithScheduleDto>` |
| `LlmController.java` | `findDoctors()` → `findDoctorsWithSchedule()` |
| `LlmControllerTest.java` | Mock 객체를 `DoctorWithScheduleDto`로 변경 |
| `index.html` | `formatSchedules()` 함수 추가, 테이블에 스케줄 렌더링 |

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

| 계층 | 구현 |
|------|------|
| Python | `/infer/medical/stream` 엔드포인트, Ollama `stream:true` → `StreamingResponse` |
| Spring | `Flux<String>` 반환, `TEXT_EVENT_STREAM_VALUE` produces |
| Frontend | `fetch` + `ReadableStream` + `data:` 파싱 |

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
    renderLlmResponse(data);  // generatedText로 AI 응답 표시
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
        add-mappings: false  # 또는 특정 경로 필터링
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
    document.getElementById('loading').classList.remove('active');
    document.getElementById('llmCard').style.display = 'block';
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
- `LlmControllerTest.java` 컴파일 오류:
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
