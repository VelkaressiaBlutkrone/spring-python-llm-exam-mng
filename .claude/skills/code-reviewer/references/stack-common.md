# 공통 (언어 무관) 체크리스트

```
□ 함수 파라미터 4개 초과
□ 함수 길이 50줄 초과
□ 중복 코드 (DRY 위반)
□ null 반환 (Optional 또는 빈 컬렉션 권장)
□ boolean 파라미터 (의미 불명확)
□ 불필요한 else (early return 후)
```

### 🟢 boolean 파라미터

```java
// ❌ true/false 의미 불명확
processOrder(orderId, true, false);

// ✅ 명명된 상수 또는 Enum
processOrder(orderId, PaymentMethod.CARD, NotificationType.NONE);

// ✅ 빌더 패턴으로 명확하게
OrderProcessCommand.builder()
    .orderId(orderId)
    .sendNotification(false)
    .usePoints(true)
    .build();
```

### 🟢 null 반환 금지

```java
// ❌ null 반환 → 호출부 null 체크 필요
public List<Order> getOrders(Long userId) {
    if (userId == null) return null;
    ...
}

// ✅ 빈 컬렉션 반환
public List<Order> getOrders(Long userId) {
    if (userId == null) return Collections.emptyList();
    ...
}

// ✅ Optional 사용 (단건 조회)
public Optional<User> findByEmail(String email) { ... }
```
