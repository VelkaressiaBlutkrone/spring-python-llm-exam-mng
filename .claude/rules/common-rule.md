# 코드 컨벤션

이 프로젝트의 소스 파일을 생성하거나 수정할 때 반드시 이 컨벤션을 따른다.
각 레이어의 상세 코드 템플릿과 예시는 `_docs/.ai/skill/` 폴더의 해당 skill을 참조한다.

---

## 패키지 구조

도메인 기반 플랫 구조를 사용한다. 레이어 기반 구조는 절대 사용하지 않는다.

```
com.example.demo/
  _core/utils/       ← 도메인 무관 공통 유틸 (Resp.java 등)
  {domain}/          ← 해당 도메인의 모든 파일을 한 폴더에 (플랫)
    {Domain}.java
    {Domain}Controller.java       ← SSR (Mustache)
    {Domain}ApiController.java    ← REST API (/api 접두사)
    {Domain}Service.java
    {Domain}Repository.java
    {Domain}Request.java
    {Domain}Response.java
```

---

## 어노테이션 순서

| 레이어         | 순서                                                                         |
| -------------- | ---------------------------------------------------------------------------- |
| Entity         | `@NoArgsConstructor` → `@Data` → `@Entity` → `@Table(name = "{도메인}_tb")` |
| Service        | `@Transactional(readOnly = true)` → `@RequiredArgsConstructor` → `@Service`  |
| Controller     | `@RequiredArgsConstructor` → `@Controller`                                   |
| RestController | `@RequiredArgsConstructor` → `@RestController` (별도 파일, `/api` 접두사)    |

---

## Entity 규칙

- PK 타입: `Integer` (`Long` 사용 금지), 전략: `GenerationType.IDENTITY`
- `@Builder`는 생성자에만 — 클래스 레벨 선언 금지
- 컬렉션 필드(`List`, `Set`)는 `@Builder` 생성자에 포함하지 않는다
- 모든 연관관계: `FetchType.LAZY` — EAGER 금지
- 생성일: `@CreationTimestamp` + `LocalDateTime createdAt`
- 테이블명: `{domain}_tb`

---

## Service 규칙

- 클래스 레벨 `@Transactional(readOnly = true)` 항상 선언
- 쓰기 메서드(`save`, `update`, `delete`)에는 `@Transactional` 개별 선언
- DTO는 Service 안에서 생성하여 반환 — 날(raw) Entity를 Controller로 전달 금지

---

## Controller 규칙

- SSR(`@Controller`)과 REST(`@RestController`)는 **별도 파일로 분리**
- REST 엔드포인트 주소는 `/api` 접두사 필수
- SSR: `HttpSession` 생성자 주입, 반환값 `String` (템플릿 경로)
- REST: `Resp.ok()` / `Resp.fail()` 사용

---

## DTO 규칙

- 도메인당 파일 하나씩: `{Domain}Request.java`, `{Domain}Response.java`
- 외부 클래스에는 어노테이션 없음 / `@Data`는 내부 static class에만
- Request 내부 클래스 이름: 기능명 (`Save`, `Update`, `Login`, `Join`)
- Response 내부 클래스 이름: 데이터 범위 기준
  - `Max`: 테이블 전체 컬럼 (상세·목록 겸용)
  - `Min`: 최소 정보 (id + 대표값)
  - `Detail`: 조인 포함 확장 정보
  - `Option`: 셀렉트박스/드롭다운용
- Entity → DTO 변환은 생성자 또는 정적 팩토리 메서드로 처리

---

## 공통 응답

- 위치: `_core/utils/Resp.java`
- 성공: `Resp.ok(dto)` (status 200)
- 실패: `Resp.fail(HttpStatus.BAD_REQUEST, "오류 메시지")`
- 모든 REST API 응답은 반드시 `Resp<T>` 래퍼 사용 — 날(raw) 반환 금지

---

## 프론트엔드 (JavaScript) 규칙

- POST 요청 기본: `<form>` 태그 + `name` 속성으로 제출 (페이지 이동 방식)
- Ajax가 필요한 경우만 fetch 사용 (중복체크, 부분 갱신 등)

---

## 네이밍

| 대상                  | 컨벤션       | 예시                             |
| --------------------- | ------------ | -------------------------------- |
| 클래스/파일           | PascalCase   | `BoardService`                   |
| 메서드/변수           | camelCase    | `findAll`                        |
| 테이블                | snake_case + `_tb` | `board_tb`                 |
| 패키지                | lowercase    | `board`, `_core`                 |
| Request 내부 클래스   | 기능명       | `Save`, `Update`, `Login`        |
| Response 내부 클래스  | 데이터 범위  | `Max`, `Min`, `Detail`, `Option` |

---

## 설정

| 규칙         | 값 / 강제 사항                                       |
| ------------ | ---------------------------------------------------- |
| OSIV         | `false` — 절대 활성화하지 않는다                     |
| Fetch 전략   | 항상 `LAZY` — `EAGER` 금지                           |
| 배치 사이즈  | `default_batch_fetch_size=10`                         |
| 인증 방식    | `HttpSession` — 별도 요청 없으면 Spring Security 금지 |
| DTO 생성     | Service 레이어에서만                                  |
| Entity 노출  | Controller에 Entity를 절대 전달하지 않는다            |
