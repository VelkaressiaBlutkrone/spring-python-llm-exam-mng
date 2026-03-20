# Spring Boot 전체 코드 리뷰

> 리뷰 일자: 2025-03-19
> 대상: `src/main/java/com/sample/llm/**` + `src/main/resources/static/**`
> 수정 상태 갱신: 2026-03-20

---

## 📊 리뷰 요약

| 등급        | 건수 | 수정 완료 | 머지 가능         |
| ----------- | ---- | --------- | ----------------- |
| 🔴 Critical | 2건  | 2건       | ✅ 수정 완료      |
| 🟡 Major    | 7건  | 6건       | ⚠️ PK 타입 미통일 |
| 🟢 Minor    | 5건  | 0건       | ✅ 선택적 수정    |
| ✅ 잘된 점  | 6건  | —         | —                 |

---

## 🔴 Critical (즉시 수정)

### 1. ~~ReservationService.java:79 — 루프 내 DB 호출로 슬롯 조회 시 대량 쿼리 발생~~ ✅ 수정 완료

> **수정됨**: `findByDoctorIdAndReservationDateBetween()` 벌크 조회 + `Set<String>` 메모리 필터링 방식으로 변경. 현재 코드가 아래 After와 동일하게 구현됨 (`ReservationService.java:57-100`).

<details>
<summary>Before/After 코드 (접기)</summary>

**Before**

```java
while (slotTime.isBefore(schedule.getEndTime())) {
    LocalTime slotEnd = slotTime.plusMinutes(30);
    if (slotEnd.isAfter(schedule.getEndTime())) break;
    long count = reservationRepository.countByDoctorIdAndReservationDateAndStartTime(
            doctorId, date, slotTime);  // ← 슬롯마다 DB 호출
    slots.add(new ReservationResponse.Slot(date, slotTime, slotEnd, count == 0));
    slotTime = slotEnd;
}
```

**After (현재 코드와 동일)**

```java
// 해당 기간 예약을 한 번에 조회
List<Reservation> existingReservations = reservationRepository
        .findByDoctorIdAndReservationDateBetween(doctorId, startDate, endDate);
Set<String> reservedKeys = existingReservations.stream()
        .map(r -> r.getReservationDate() + "_" + r.getStartTime())
        .collect(Collectors.toSet());
```

</details>

---

### 2. ~~MedicalController.java:46-52, ChatController.java:44-49 — Reactive 체인 내에서 @Transactional 동기 메서드 호출~~ ✅ 수정 완료

> **수정됨**: `Mono.block()` 동기화 방식으로 전환. 현재 `MedicalController.java:50`에서 `.block()`으로 응답을 동기 수신 후 트랜잭션 메서드 호출. `ChatController.java:41`도 동일 패턴.

<details>
<summary>Before/After 코드 (접기)</summary>

**Before**

```java
return medicalService.callLlmApi(request.getQuery())
        .doOnNext(response -> {
            medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
        });
```

**After (현재 코드)**

```java
String response = medicalService.callLlmApi(request.getQuery()).block();
long latencyMs = System.currentTimeMillis() - startTime;
medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
return response;
```

</details>

---

## 🟡 Major (수정 권고)

### 1. ~~MedicalService.java:37-54 vs 56-77 — callLlmApi()와 callMedicalLlmApi() 완전 중복~~ ✅ 수정 완료

> **수정됨**: `callLlmApi()`가 `callMedicalLlmApi()`에 위임하는 방식으로 중복 제거 (현재 `MedicalService.java:40-43`).

---

### 2. ~~ReservationApiController.java:27-37 — Controller에서 직접 try-catch, GlobalExceptionHandler 우회~~ ✅ 수정 완료

> **수정됨**: try-catch 제거, `GlobalExceptionHandler`에 위임. 현재 `ReservationApiController.java:24-29`는 예외를 직접 처리하지 않음.

---

### 3. ~~Doctor.java:34, DoctorSchedule.java:29 — @ManyToOne에 FetchType.LAZY 누락~~ ✅ 수정 완료

> **수정됨**: 두 엔티티 모두 `fetch = FetchType.LAZY` 추가됨.
> - `Doctor.java:35` — `@ManyToOne(fetch = FetchType.LAZY)`
> - `DoctorSchedule.java:29` — `@ManyToOne(fetch = FetchType.LAZY)`

---

### 4. ~~DoctorService.java:45-58 — 의사 목록 조회 후 스케줄 N+1 쿼리~~ ✅ 수정 완료

> **수정됨**: `findByDoctorIdInAndIsAvailableTrue(doctorIds)` IN 쿼리 + `Collectors.groupingBy` 패턴 적용. 현재 코드가 After와 동일 (`DoctorService.java:52-64`).

---

### 5. ~~MedicalService.java:117-123 — updateMedicalCompleted()에서 ifPresent로 조용히 무시~~ ✅ 수정 완료

> **수정됨**: `orElseThrow()` 패턴으로 변경. `updateMedicalCompleted()` (현재 `MedicalService.java:105-112`)와 `updateMedicalFailed()` (현재 `MedicalService.java:115-123`) 모두 동일 패턴 적용.

---

### 6. Entity 전반 — PK 타입 불일치 (Long vs Integer 혼용)

**문제**: `Reservation`, `MedicalRule`은 `Integer` PK, 나머지(`ChatHistory`, `Doctor`, `Staff` 등)는 `Long` PK를 사용합니다. 프로젝트 컨벤션은 `Integer` + `IDENTITY`이지만 실제로는 혼재되어 있어, `ReservationRepository`의 제네릭 타입(`JpaRepository<Reservation, Integer>`)과 Controller의 `Long doctorId` 등에서 타입 불일치가 발생할 수 있습니다.

**권고**: 통일 방향을 결정하고 일관되게 적용

---

### 7. ~~ChatController.java:30, MedicalController.java:35 — Controller에서 Repository 직접 주입~~ ✅ 수정 완료

> **수정됨**: Repository 직접 주입 제거. 히스토리 조회가 Service 레이어로 이동됨.
> - `ChatController.java:28` — `chatService`만 주입, `chatService.getChatHistory()` 호출 (line 67)
> - `MedicalController.java:35` — `medicalService`만 주입, `medicalService.getMedicalHistory()` 호출 (line 136)

---

## 🟢 Minor (선택적)

### 1. Entity 전반 — status 필드에 String 사용

`MedicalHistory.status` ("PENDING", "COMPLETED", "FAILED")와 `Reservation.status` ("CONFIRMED")가 문자열로 관리됩니다. 오타 위험이 있으므로 Enum 사용을 권장합니다.

```java
public enum MedicalHistoryStatus {
    PENDING, COMPLETED, FAILED
}

public enum ReservationStatus {
    CONFIRMED, CANCELLED
}
```

---

### 2. DoctorService.java:16-17 — 어노테이션 순서 컨벤션 불일치

**컨벤션**: `@Transactional(readOnly=true)` → `@RequiredArgsConstructor` → `@Service`

**실제**: `@Service` → `@RequiredArgsConstructor` → `@Slf4j` → `@Transactional`

---

### 3. Entity 전반 — 테이블명 `_tb` 접미사 누락

컨벤션은 `{domain}_tb`이지만 `Reservation`만 `reservation_tb`를 사용하고, 나머지(`chatbot_history`, `doctor`, `staff`, `medical_history` 등)는 접미사 없이 사용합니다.

---

### 4. MedicalService.java:19-20 — tools.jackson 패키지 import

`tools.jackson.core.JacksonException`과 `tools.jackson.databind.ObjectMapper`는 Jackson 3.x (tools.jackson) 패키지입니다. 프로젝트 전체의 Jackson 버전 일관성을 확인해야 합니다.

---

### 5. ReservationRequest.java — 입력값 검증 누락

`ReservationRequest.Save`에 `@NotNull`, `@Future` 등의 Bean Validation 어노테이션이 없어 null doctorId나 과거 날짜 예약이 가능합니다.

```java
@Data
public static class Save {
    @NotNull(message = "의사 ID는 필수입니다")
    private Long doctorId;

    @NotNull @Future(message = "예약 날짜는 미래여야 합니다")
    private LocalDate reservationDate;

    @NotNull
    private LocalTime startTime;

    @NotNull
    private LocalTime endTime;
}
```

---

## ✅ 잘된 점

1. **WebClient 에러 처리 체계적**: `onErrorMap()`으로 커스텀 예외(`LlmTimeoutException`, `LlmServiceUnavailableException`)를 잘 분류하고, `GlobalExceptionHandler`에서 적절한 HTTP 상태 코드(503, 504)로 매핑

2. **DTO 분리 일관적**: Entity를 Controller에 직접 반환하지 않고, 모든 응답이 DTO(`ChatHistoryResponse`, `MedicalHistoryResponse`, `DoctorDto` 등)를 통해 변환

3. **SSE 스트리밍 + 폴백 구현**: 프론트엔드에서 SSE 스트리밍을 먼저 시도하고 실패 시 일반 API로 자동 폴백하는 패턴이 잘 설계

4. **DataLoader의 @Profile("!test")**: 테스트 환경에서 시드 데이터가 실행되지 않도록 프로필 분리

5. **XSS 방어**: `chat.html`의 `escapeHtml()` 함수가 `textContent`를 이용한 안전한 이스케이프 수행

6. **LlmResponseParser 정규표현식 분리**: LLM 응답 파싱 로직이 별도 컴포넌트로 잘 분리되어 테스트 가능

---

## 💬 PR 코멘트 (수정 이력)

> 아래 코멘트의 모든 Critical/Major 이슈(PK 타입 통일 제외)는 **수정 완료**되었습니다. (2026-03-20 확인)

```
✅ [Critical] ReservationService — N+1 해소. findByDoctorIdAndReservationDateBetween 벌크 조회로 변경.
✅ [Critical] MedicalController, ChatController — .block() 동기화로 트랜잭션 보장.
✅ [Major] MedicalService — callLlmApi()가 callMedicalLlmApi()에 위임하여 중복 제거.
✅ [Major] ReservationApiController — try-catch 제거, GlobalExceptionHandler 위임.
✅ [Major] Doctor, DoctorSchedule — FetchType.LAZY 추가.
✅ [Major] DoctorService — findByDoctorIdInAndIsAvailableTrue IN 쿼리로 N+1 해소.
✅ [Major] MedicalService — ifPresent → orElseThrow 변경.
✅ [Major] ChatController, MedicalController — Repository 직접 주입 제거, Service로 이동.
⬜ [Major] Entity PK 타입 Long/Integer 혼재 — 미수정 (통일 방향 결정 필요).
```

---

_🔴 Critical 2건 수정 완료. Minor 이슈(어노테이션 순서, 테이블명 `_tb`, Jackson 버전, 입력 검증)는 미수정._
