# LLM 샘플 관리 시스템 - 제품 요구사항 문서 (PRD)

## 1. 시스템 개요

사용자가 요청한 LLM 시스템은 **Spring Boot**(백엔드 프레임워크), **MySQL**(데이터베이스), **Python**(LLM 처리)을 사용하여 구축하되, **RAG(Retrieval-Augmented Generation)**나 **벡터 데이터베이스**를 사용하지 않습니다.

이는 **순수 LLM 추론(inference)**을 기반으로 한 간단한 시스템을 의미하며, 예를 들어 사용자 쿼리를 받아 LLM으로 응답을 생성하고, MySQL에 챗 히스토리나 사용자 데이터를 저장하는 형태로 설계합니다.

### 주요 가정

| 가정        | 설명                                                                   |
| ----------- | ---------------------------------------------------------------------- |
| LLM 소스    | 외부 모델(OpenAI GPT, Hugging Face 모델 등)을 사용하거나 로컬로 호스팅 |
| RAG 제외    | 외부 지식 검색 없이 LLM의 기본 지식만 활용                             |
| 시스템 목적 | 간단한 챗봇이나 텍스트 생성 API (e.g., 질문-답변, 요약 생성)           |
| 통합 방식   | Spring Boot에서 Python 스크립트나 서버를 호출하여 LLM 추론 수행        |

---

## 2. 아키텍처 다이어그램 (텍스트 기반)

```text
[클라이언트 (e.g., 웹/모바일 앱)]
    ↓ (HTTP 요청)
[Spring Boot 서버]
    - REST API 엔드포인트 (e.g., /api/llm/query)
    - MySQL 연결 (JPA/Hibernate): 챗 히스토리 저장/조회
    ↓ (비동기 HTTP 호출 권장: WebClient)
[Python LLM 서버]
    - FastAPI (비동기 처리 최적화)
    - Uvicorn/Gunicorn 워커로 병렬 처리
    - LLM 모델 로딩, 추론 수행
    ↑ (응답 반환)
[Spring Boot 서버] → 클라이언트 응답
```

### 2.1 비동기 처리 권고

LLM 추론은 모델 크기에 따라 **수 초~수십 초**가 소요됩니다. RestTemplate(동기) 방식은 응답 대기 동안 커넥션을 점유하여 타임아웃·성능 저하를 유발할 수 있습니다.

| 방식                 | 권고   | 설명                                                                     |
| -------------------- | ------ | ------------------------------------------------------------------------ |
| **Spring WebClient** | 권장   | 비동기 호출로 커넥션 효율 향상                                           |
| **상태값 관리**      | 권장   | chat_history에 status (PENDING, COMPLETED) 추가, 폴링/콜백으로 완료 확인 |
| RestTemplate         | 비권장 | 동기 호출, 장시간 대기 시 부적합                                         |

---

## 3. 주요 컴포넌트 설계

| 컴포넌트               | 역할                                  | 기술 스택                                            | 상세 설명                                                                                                                                          |
| ---------------------- | ------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Spring Boot 백엔드** | API 서버, 비즈니스 로직 처리, DB 연결 | Spring Boot 3.x, Spring Web/WebFlux, Spring Data JPA | REST 컨트롤러로 쿼리 수신. **WebClient**로 Python 비동기 호출 권장. chat_history에 status(PENDING/COMPLETED) 저장. LangChain4j/Spring AI 대안 존재 |
| **MySQL 데이터베이스** | 데이터 저장                           | MySQL 8.x                                            | users, chat_history 테이블. session_id로 대화 그룹화, metadata(JSON)로 성능 분석                                                                   |
| **Python LLM 모듈**    | LLM 추론                              | Python 3.x, FastAPI, Uvicorn/Gunicorn                | FastAPI는 비동기 최적화. **Uvicorn/Gunicorn 워커 설정**으로 병렬 처리 확보. transformers 또는 vLLM/TGI 서빙 엔진                                   |
| **통합 메커니즘**      | Spring Boot ↔ Python                  | HTTP (REST)                                          | Python FastAPI HTTP POST 호출. API 키/JWT 인증. Python 다운 시 503 반환 정의                                                                       |

---

## 4. 데이터 모델

### 4.1 users 테이블

| 컬럼     | 타입        | 설명               |
| -------- | ----------- | ------------------ |
| id       | BIGINT (PK) | 사용자 고유 식별자 |
| username | VARCHAR     | 사용자명           |
| email    | VARCHAR     | 이메일 주소        |

### 4.2 chat_history 테이블

| 컬럼       | 타입        | 설명                                            |
| ---------- | ----------- | ----------------------------------------------- |
| id         | BIGINT (PK) | 히스토리 고유 식별자                            |
| user_id    | BIGINT (FK) | 사용자 ID                                       |
| session_id | VARCHAR(64) | 세션/대화 그룹 ID (같은 주제 대화 묶음)         |
| query      | TEXT        | 사용자 쿼리                                     |
| response   | TEXT        | LLM 응답                                        |
| status     | VARCHAR(20) | PENDING(처리 중), COMPLETED(완료), FAILED(실패) |
| metadata   | JSON        | 모델명, latency(ms), token_usage 등 성능 분석용 |
| timestamp  | DATETIME    | 생성 시각                                       |

**세션 그룹화**: 하나의 주제로 이어지는 대화를 `session_id`로 묶어 조회·관리.

**메타데이터 예시** (JSON):

```json
{
  "model": "gpt2",
  "latency_ms": 1250,
  "input_tokens": 10,
  "output_tokens": 50
}
```

---

## 5. 구현 단계

### 5.1 환경 설정

1. **Spring Boot 프로젝트 생성**
   - Spring Initializr로 Web, **WebFlux**(WebClient용), JPA, MySQL 드라이버 추가

2. **MySQL 설치**

   ```bash
   docker run -p 3306:3306 --name mysql -e MYSQL_ROOT_PASSWORD=password -d mysql:8
   ```

3. **Python 환경**

   ```bash
   pip install fastapi uvicorn transformers
   ```

   (Hugging Face 모델용)

### 5.2 Spring Boot 구현 예시

#### application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/llm_db
    username: root
    password: password
  jpa:
    hibernate:
      ddl-auto: update
```

#### Controller 예시 (WebClient 비동기 권장)

```java
@RestController
@RequestMapping("/api/llm")
public class LlmController {
    @Autowired private ChatHistoryRepository repo;
    @Autowired private WebClient.Builder webClientBuilder;

    @PostMapping("/query")
    public Mono<String> handleQuery(@RequestBody String query) {
        // PENDING 상태로 먼저 저장 (선택)
        ChatHistory history = new ChatHistory();
        history.setQuery(query);
        history.setStatus("PENDING");
        repo.save(history);

        // WebClient 비동기 호출
        return webClientBuilder.build()
            .post().uri("http://localhost:8000/infer")
            .bodyValue(Map.of("query", query))
            .retrieve()
            .bodyToMono(InferResponse.class)
            .map(r -> r.getGeneratedText())
            .doOnNext(response -> {
                history.setResponse(response);
                history.setStatus("COMPLETED");
                repo.save(history);
            });
    }
}
```

#### Entity 예시 (보완)

```java
@Entity
public class ChatHistory {
    @Id @GeneratedValue private Long id;
    private Long userId;
    private String sessionId;
    private String query;
    private String response;
    private String status;  // PENDING, COMPLETED, FAILED
    @Column(columnDefinition = "JSON") private String metadata;
    private LocalDateTime timestamp = LocalDateTime.now();
    // getters/setters
}
```

### 5.3 Python 구현 예시

#### FastAPI 서버 (app.py)

```python
from fastapi import FastAPI, Body
from transformers import pipeline

app = FastAPI()
generator = pipeline('text-generation', model='gpt2')

@app.post("/infer")
def infer(query: str = Body(...)):
    result = generator(query, max_length=100, num_return_sequences=1)
    return result[0]['generated_text']

# 실행: uvicorn app:app --workers 2 --reload
# Gunicorn: gunicorn app:app -w 2 -k uvicorn.workers.UvicornWorker
```

#### Python 전처리 (Pre-processing)

LLM에 전달하기 전 입력 텍스트 전처리 단계를 정의합니다.

| 항목                | 설명                                    |
| ------------------- | --------------------------------------- |
| **길이 제한**       | 입력 텍스트 최대 길이 제한 (예: 2048자) |
| **개인정보 마스킹** | 이메일, 전화번호 등 PII 마스킹 (선택)   |
| **특수문자 정규화** | 연속 공백, 제어문자 제거                |

#### Exception Handling (Spring Boot → Python)

Python 서버 장애 시 Spring Boot에서 반환할 에러 응답:

| 상황                  | HTTP 상태               | 응답                                          |
| --------------------- | ----------------------- | --------------------------------------------- |
| Python 서버 연결 실패 | 503 Service Unavailable | `{"detail": "LLM 서버를 사용할 수 없습니다"}` |
| Python 타임아웃       | 504 Gateway Timeout     | `{"detail": "LLM 응답 시간 초과"}`            |
| Python 5xx 에러       | 503                     | Python 에러 메시지 전달                       |

> **참고**: 로컬 LLM 호스팅 시, Ollama나 Llama.cpp 사용 가능 (Python wrapper).

---

## 6. 보안 및 성능 고려

| 항목            | 고려사항                                                    |
| --------------- | ----------------------------------------------------------- |
| **인증**        | Spring Security로 API 보호                                  |
| **스케일링**    | Python 서버를 Docker로 컨테이너화, Kubernetes 배포          |
| **에러 핸들링** | LLM 호출 실패 시 fallback (e.g., 기본 응답)                 |
| **성능**        | 비동기 처리 (Spring WebClient), Python 워커 설정            |
| **비용**        | 로컬 LLM 사용 시 GPU 필요; 클라우드 API (e.g., OpenAI) 대안 |

### 6.1 모델 서빙 최적화

transformers 파이프라인을 그대로 사용하는 것보다, 전용 서빙 엔진을 사용하면 처리 속도가 **수 배 향상**됩니다.

| 방식                                | 설명                             | 권장 상황             |
| ----------------------------------- | -------------------------------- | --------------------- |
| **vLLM**                            | 고성능 PagedAttention, 배치 처리 | 로컬 LLM, 대규모 추론 |
| **TGI (Text Generation Inference)** | Hugging Face 공식, 배치·스트리밍 | 프로덕션 배포         |
| transformers pipeline               | 직접 사용                        | 프로토타입, 소규모    |

---

## 7. 잠재적 확장

| 확장 항목                  | 설명                                                                  |
| -------------------------- | --------------------------------------------------------------------- |
| **다중 LLM 지원**          | Python에서 모델 스위칭                                                |
| **히스토리 기반 프롬프트** | MySQL에서 과거 챗 불러와 LLM 프롬프트에 추가 (RAG 아닌 단순 컨텍스트) |
| **테스트**                 | JUnit으로 Spring Boot 테스트, pytest로 Python 테스트                  |

---

## 8. API 명세

### 8.1 LLM 쿼리 API

| 항목           | 내용                                                |
| -------------- | --------------------------------------------------- |
| **엔드포인트** | `POST /api/llm/query`                               |
| **요청**       | `Content-Type: application/json`, Body: 쿼리 텍스트 |
| **응답**       | LLM 생성 응답 텍스트                                |
| **부가 동작**  | 응답을 chat_history 테이블에 저장                   |

---

## 9. 용어 정의

| 용어                | 정의                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------- |
| **RAG**             | Retrieval-Augmented Generation, 외부 지식 검색을 통해 LLM 응답을 보강하는 방식 (본 시스템에서는 미사용) |
| **LLM**             | Large Language Model, 대규모 언어 모델                                                                  |
| **추론(Inference)** | 학습된 모델에 입력을 넣어 출력을 생성하는 과정                                                          |

---

## 10. 문서 이력

| 버전 | 날짜       | 작성자 | 변경 내용                                                                               |
| ---- | ---------- | ------ | --------------------------------------------------------------------------------------- |
| 1.0  | 2025-02-26 | -      | 최초 작성                                                                               |
| 1.1  | 2025-02-26 | -      | 비동기 처리 권고, session_id/metadata, 전처리, Exception Handling, vLLM/TGI 서빙 최적화 |
