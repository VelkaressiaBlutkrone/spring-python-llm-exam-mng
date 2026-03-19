# Spring Boot 전체 코드 리뷰

> 리뷰 일자: 2025-03-19
> 대상: `src/main/java/com/sample/llm/**` + `src/main/resources/static/**`

---

## 📊 리뷰 요약

| 등급        | 건수 | 머지 가능         |
| ----------- | ---- | ----------------- |
| 🔴 Critical | 2건  | ❌ 즉시 수정 필요 |
| 🟡 Major    | 7건  | ⚠️ 수정 권고      |
| 🟢 Minor    | 5건  | ✅ 선택적 수정    |
| ✅ 잘된 점  | 6건  | —                 |

---

## 🔴 Critical (즉시 수정)

### 1. ReservationService.java:79 — 루프 내 DB 호출로 슬롯 조회 시 대량 쿼리 발생

**위치**: `ReservationService.getAvailableSlots()`

**문제**: 7일 x 스케줄 수 x 30분 슬롯마다 `countByDoctorIdAndReservationDateAndStartTime()`을 개별 호출합니다. 의사 1명에 하루 8시간이면 슬롯 16개 x 7일 = **최대 112회 DB 쿼리**가 발생합니다.

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

**After**

```java
public ReservationResponse.SlotList getAvailableSlots(Long doctorId) {
    Doctor doctor = doctorRepository.findById(doctorId)
            .orElseThrow(() -> new IllegalArgumentException("Doctor not found: " + doctorId));

    var schedules = doctorScheduleRepository.findByDoctorIdAndIsAvailableTrue(doctorId);

    LocalDate today = LocalDate.now();
    LocalDate endDate = today.plusDays(8);

    // 해당 기간 예약을 한 번에 조회
    List<Reservation> existingReservations = reservationRepository
            .findByDoctorIdAndReservationDateBetween(doctorId, today.plusDays(1), endDate);

    Set<String> reservedKeys = existingReservations.stream()
            .map(r -> r.getReservationDate() + "_" + r.getStartTime())
            .collect(Collectors.toSet());

    List<ReservationResponse.Slot> slots = new ArrayList<>();
    for (int dayOffset = 1; dayOffset <= 7; dayOffset++) {
        LocalDate date = today.plusDays(dayOffset);
        String dayCode = toEnglishDayCode(date.getDayOfWeek());
        schedules.stream()
                .filter(s -> s.getDayOfWeek().equalsIgnoreCase(dayCode))
                .forEach(schedule -> {
                    LocalTime slotTime = schedule.getStartTime();
                    while (slotTime.isBefore(schedule.getEndTime())) {
                        LocalTime slotEnd = slotTime.plusMinutes(30);
                        if (slotEnd.isAfter(schedule.getEndTime())) break;
                        boolean available = !reservedKeys.contains(date + "_" + slotTime);
                        slots.add(new ReservationResponse.Slot(date, slotTime, slotEnd, available));
                        slotTime = slotEnd;
                    }
                });
        if (slots.size() >= 12) break;
    }
    return new ReservationResponse.SlotList(doctorId, doctor.getName(), slots);
}
```

**필요 추가 작업**: `ReservationRepository`에 아래 메서드 추가

```java
List<Reservation> findByDoctorIdAndReservationDateBetween(
        Long doctorId, LocalDate startDate, LocalDate endDate);
```

---

### 2. MedicalController.java:46-52, ChatController.java:44-49 — Reactive 체인 내에서 @Transactional 동기 메서드 호출

**위치**: `MedicalController.handleQuery()`, `ChatController.handleRuleQuery()`

**문제**: `doOnNext()` 콜백은 Reactor 스케줄러 스레드에서 실행되어 Spring의 `@Transactional` 프록시가 적용되지 않을 수 있습니다. `saveMedicalPending()`은 Reactive 체인 밖에서 호출되지만, `updateMedicalCompleted()`는 `doOnNext()` 안에서 호출됩니다.

**Before**

```java
return medicalService.callLlmApi(request.getQuery())
        .doOnNext(response -> {
            medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
        });
```

**After**

```java
return medicalService.callLlmApi(request.getQuery())
        .map(response -> {
            long latencyMs = System.currentTimeMillis() - startTime;
            medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
            return response;
        })
        .subscribeOn(Schedulers.boundedElastic()); // 블로킹 작업을 별도 스레드풀에서
```

> 또는 `updateMedicalCompleted()` 내부에서 `TransactionTemplate`을 사용하여 프로그래밍적으로 트랜잭션을 보장하는 방법도 있습니다.

---

## 🟡 Major (수정 권고)

### 1. MedicalService.java:37-54 vs 56-77 — callLlmApi()와 callMedicalLlmApi() 완전 중복

**문제**: 두 메서드가 동일한 URI `/infer/medical`, 동일한 파라미터, 동일한 에러 처리를 가지며 로그 메시지만 다릅니다.

**Before**

```java
public Mono<String> callLlmApi(String query) { /* /infer/medical */ }
public Mono<String> callMedicalLlmApi(String query) { /* /infer/medical */ }
```

**After**

```java
public Mono<String> callMedicalLlmApi(String query) {
    log.debug("Medical LLM API 호출 시작 - query: {}", query);
    return callLlmEndpoint("/infer/medical", query, "Medical LLM");
}

private Mono<String> callLlmEndpoint(String uri, String query, String label) {
    return llmWebClient.post()
            .uri(uri)
            .bodyValue(Map.of("query", query, "max_length", 512, "temperature", 0.3))
            .retrieve()
            .bodyToMono(LlmResponse.class)
            .map(LlmResponse::getGeneratedText)
            .onErrorMap(WebClientRequestException.class, e -> {
                if (e.getCause() instanceof ConnectTimeoutException) {
                    return new LlmTimeoutException(label + " 서버 연결 타임아웃", e);
                }
                return new LlmServiceUnavailableException(label + " 서버 연결 실패", e);
            })
            .onErrorMap(TimeoutException.class, e ->
                    new LlmTimeoutException(label + " 응답 시간 초과", e));
}
```

---

### 2. ReservationApiController.java:27-37 — Controller에서 직접 try-catch, GlobalExceptionHandler 우회

**문제**: `GlobalExceptionHandler`가 이미 존재하는데 Controller에서 `IllegalStateException`, `IllegalArgumentException`을 직접 catch합니다. 응답 형식도 다른 API(`ErrorResponse`)와 불일치(`Map.of("error", ...)`)합니다.

**Before**

```java
@PostMapping
public ResponseEntity<?> createReservation(@RequestBody ReservationRequest.Save request) {
    try {
        ReservationResponse.Max result = reservationService.createReservation(request);
        return ResponseEntity.ok(result);
    } catch (IllegalStateException e) {
        return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
    } catch (IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
    }
}
```

**After**

```java
@PostMapping
public ResponseEntity<ReservationResponse.Max> createReservation(
        @RequestBody ReservationRequest.Save request) {
    ReservationResponse.Max result = reservationService.createReservation(request);
    return ResponseEntity.ok(result);
}

// GlobalExceptionHandler에 추가
@ExceptionHandler({IllegalStateException.class, IllegalArgumentException.class})
public ResponseEntity<ErrorResponse> handleIllegalArgument(RuntimeException e) {
    return ResponseEntity.badRequest().body(new ErrorResponse(e.getMessage()));
}
```

---

### 3. Doctor.java:34, DoctorSchedule.java:29 — @ManyToOne에 FetchType.LAZY 누락

**문제**: `Doctor.medicalDomain`과 `DoctorSchedule.doctor`에 `fetch = FetchType.LAZY`가 지정되지 않아 기본값 `EAGER`로 동작합니다. 프로젝트 컨벤션(common-rule.md)에서 **모든 연관관계는 LAZY** 필수입니다.

**Before**

```java
@ManyToOne
@JoinColumn(name = "domain_id")
private MedicalDomain medicalDomain;

@ManyToOne
@JoinColumn(name = "doctor_id", nullable = false)
private Doctor doctor;
```

**After**

```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "domain_id")
private MedicalDomain medicalDomain;

@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "doctor_id", nullable = false)
private Doctor doctor;
```

---

### 4. DoctorService.java:45-58 — 의사 목록 조회 후 스케줄 N+1 쿼리

**문제**: `findDoctorsWithSchedule()`에서 의사 목록을 가져온 뒤 각 의사마다 `findByDoctorIdAndIsAvailableTrue()`를 호출합니다. 의사 10명이면 1 + 10 = 11회 쿼리입니다.

**Before**

```java
return doctors.stream()
        .map(doctor -> {
            List<DoctorScheduleDto> schedules = doctorScheduleRepository
                    .findByDoctorIdAndIsAvailableTrue(doctor.getId()) // N+1
                    .stream().map(DoctorScheduleDto::from).toList();
            return DoctorWithScheduleDto.from(doctor, schedules);
        }).toList();
```

**After**

```java
List<Long> doctorIds = doctors.stream().map(Doctor::getId).toList();
List<DoctorSchedule> allSchedules = doctorScheduleRepository
        .findByDoctorIdInAndIsAvailableTrue(doctorIds);

Map<Long, List<DoctorScheduleDto>> scheduleMap = allSchedules.stream()
        .collect(Collectors.groupingBy(
                s -> s.getDoctor().getId(),
                Collectors.mapping(DoctorScheduleDto::from, Collectors.toList())));

return doctors.stream()
        .map(doctor -> DoctorWithScheduleDto.from(doctor,
                scheduleMap.getOrDefault(doctor.getId(), List.of())))
        .toList();
```

**필요 추가 작업**: `DoctorScheduleRepository`에 아래 메서드 추가

```java
List<DoctorSchedule> findByDoctorIdInAndIsAvailableTrue(List<Long> doctorIds);
```

---

### 5. MedicalService.java:117-123 — updateMedicalCompleted()에서 ifPresent로 조용히 무시

**문제**: `findById()` 결과가 없으면 아무 동작 없이 넘어갑니다. PENDING 상태로 저장된 직후 조회이므로 발견되지 않는 건 시스템 오류인데, 이를 무시하면 데이터 불일치를 파악하기 어렵습니다.

**Before**

```java
medicalHistoryRepository.findById(historyId).ifPresent(history -> {
    history.setAnswer(answer);
    history.setStatus("COMPLETED");
    history.setMetadata(buildMetadata(latencyMs));
    medicalHistoryRepository.save(history);
});
```

**After**

```java
MedicalHistory history = medicalHistoryRepository.findById(historyId)
        .orElseThrow(() -> new IllegalStateException(
                "MedicalHistory not found: " + historyId));
history.setAnswer(answer);
history.setStatus("COMPLETED");
history.setMetadata(buildMetadata(latencyMs));
// 영속성 컨텍스트 내이므로 save() 불필요 (dirty checking)
```

---

### 6. Entity 전반 — PK 타입 불일치 (Long vs Integer 혼용)

**문제**: `Reservation`, `MedicalRule`은 `Integer` PK, 나머지(`ChatHistory`, `Doctor`, `Staff` 등)는 `Long` PK를 사용합니다. 프로젝트 컨벤션은 `Integer` + `IDENTITY`이지만 실제로는 혼재되어 있어, `ReservationRepository`의 제네릭 타입(`JpaRepository<Reservation, Integer>`)과 Controller의 `Long doctorId` 등에서 타입 불일치가 발생할 수 있습니다.

**권고**: 통일 방향을 결정하고 일관되게 적용

---

### 7. ChatController.java:30, MedicalController.java:35 — Controller에서 Repository 직접 주입

**문제**: `ChatController`에 `ChatHistoryRepository`, `MedicalController`에 `MedicalHistoryRepository`가 직접 주입되어 Service 레이어를 우회합니다.

**Before**

```java
private final ChatHistoryRepository chatHistoryRepository;

@GetMapping("/history/{staffId}")
public Page<ChatHistoryResponse> getRuleHistory(...) {
    return chatHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
            .map(ChatHistoryResponse::from);
}
```

**After**

```java
// ChatService에 메서드 추가
public Page<ChatHistoryResponse> getChatHistory(Long staffId, Pageable pageable) {
    return chatHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
            .map(ChatHistoryResponse::from);
}

// Controller
@GetMapping("/history/{staffId}")
public Page<ChatHistoryResponse> getRuleHistory(...) {
    return chatService.getChatHistory(staffId, pageable);
}
```

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

## 💬 PR 코멘트 (복사용)

```
🔴 [Critical] ReservationService:79 — 루프 내 DB 호출 N+1
getAvailableSlots()에서 슬롯마다 countBy 쿼리를 호출합니다.
7일 x 슬롯 수 = 최대 112회 쿼리. 기간 내 예약을 한 번에 조회 후 메모리에서 필터하세요.

🔴 [Critical] MedicalController:46-52, ChatController:44-49 — doOnNext 내 @Transactional 미보장
Reactor 콜백 스레드에서 Spring @Transactional 프록시가 동작하지 않을 수 있습니다.
subscribeOn(Schedulers.boundedElastic()) 또는 TransactionTemplate 사용을 권장합니다.

🟡 [Major] MedicalService:37-77 — callLlmApi()와 callMedicalLlmApi() 완전 중복
동일한 URI, 파라미터, 에러 처리. 하나의 private 헬퍼로 통합하세요.

🟡 [Major] ReservationApiController:27-37 — GlobalExceptionHandler 우회
다른 API는 ErrorResponse로 반환하는데 여기만 Map.of("error", ...) 반환. 응답 형식 불일치.

🟡 [Major] Doctor:34, DoctorSchedule:29 — FetchType.LAZY 누락
컨벤션 위반. 모든 @ManyToOne에 fetch = FetchType.LAZY 필수.

🟡 [Major] DoctorService:45-58 — 의사별 스케줄 N+1 쿼리
findByDoctorIdInAndIsAvailableTrue(doctorIds)로 IN 쿼리 한 번에 조회하세요.

🟡 [Major] MedicalService:117 — ifPresent로 조용한 실패
PENDING 직후 조회 실패는 시스템 오류. orElseThrow로 변경하세요.

🟡 [Major] ChatController:69, MedicalController:35 — Controller에 Repository 직접 주입
Service 레이어를 우회합니다. 히스토리 조회를 Service로 이동하세요.
```

---

_🔴 Critical 2건 수정 후 머지 가능합니다._
