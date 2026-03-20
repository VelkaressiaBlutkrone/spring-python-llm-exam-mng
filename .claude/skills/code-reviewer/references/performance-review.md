# 성능 리뷰 체크리스트

---

## 공통 성능 체크리스트

```
□ 루프 안에서 DB/외부 API 호출 (N+1)
□ 불필요한 전체 데이터 로딩 (페이지네이션 누락)
□ 인덱스 없는 컬럼 조회
□ 캐시 적용 가능한 데이터를 매번 조회
□ 불필요한 객체 생성 (루프 내 String 연결 등)
□ 동기 처리 가능 → 비동기로 개선 가능한 작업
□ 스트림/컬렉션 불필요한 다중 순회
```

---

## 🟡 N+1 쿼리

**탐지 패턴**
```java
// ❌ N+1: 주문 목록 조회 후 각 주문마다 아이템 조회
List<Order> orders = orderRepository.findAll();  // 쿼리 1번
for (Order order : orders) {
    List<OrderItem> items = order.getItems();     // 주문 수만큼 추가 쿼리
    total += items.size();
}

// ❌ 서비스에서 루프 내 Repository 호출
List<Long> userIds = ...;
for (Long userId : userIds) {
    User user = userRepository.findById(userId).orElseThrow(); // N번
    sendEmail(user.getEmail());
}
```

**개선 코드**
```java
// ✅ Fetch Join
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.status = :status")
List<Order> findByStatusWithItems(@Param("status") OrderStatus status);

// ✅ @EntityGraph
@EntityGraph(attributePaths = {"items", "items.product"})
List<Order> findAll();

// ✅ @BatchSize (컬렉션 지연 로딩 최적화)
// application.yml
// spring.jpa.properties.hibernate.default_batch_fetch_size: 100

// ✅ 루프 대신 IN 쿼리
List<User> users = userRepository.findAllById(userIds);  // 한 번에
users.forEach(user -> sendEmail(user.getEmail()));
```

**PR 코멘트**
```
🟡 **[Major] N+1 쿼리 발생**
주문 100건 조회 시 아이템 조회 쿼리가 100번 추가 실행됩니다.
`JOIN FETCH` 또는 `@EntityGraph`로 단일 쿼리로 최적화해주세요.
```

---

## 🟡 페이지네이션 없는 전체 조회

**탐지 패턴**
```java
// ❌ 전체 데이터 메모리 로딩
List<Order> allOrders = orderRepository.findAll();  // 100만 건도 전부 로딩
return allOrders.stream()
    .filter(o -> o.getStatus() == PENDING)
    .collect(toList());
```

**개선 코드**
```java
// ✅ 조건 + 페이지네이션을 DB에서 처리
Page<Order> orders = orderRepository.findByStatus(PENDING,
    PageRequest.of(page, size, Sort.by("createdAt").descending()));

// ✅ 대량 처리는 Slice 또는 Cursor 기반
Slice<Order> slice = orderRepository.findByStatusOrderByIdAsc(
    PENDING, PageRequest.of(0, 100));
```

---

## 🟡 캐시 누락

**탐지 패턴**
```java
// ❌ 변경 없는 데이터를 매 요청마다 조회
public List<Category> getAllCategories() {
    return categoryRepository.findAll();  // DB 히트 매번
}

// ❌ 외부 API를 매번 호출
public ExchangeRate getRate(String currency) {
    return exchangeRateApiClient.fetch(currency);  // API 매번 호출
}
```

**개선 코드**
```java
// ✅ @Cacheable 적용 (Spring Cache + Redis)
@Cacheable(value = "categories", unless = "#result.isEmpty()")
public List<Category> getAllCategories() {
    return categoryRepository.findAll();
}

// ✅ 외부 API 캐시 (TTL 설정)
@Cacheable(value = "exchangeRates", key = "#currency")
public ExchangeRate getRate(String currency) {
    return exchangeRateApiClient.fetch(currency);
}

// ✅ 캐시 무효화 (데이터 변경 시)
@CacheEvict(value = "categories", allEntries = true)
public Category createCategory(CategoryRequest request) { ... }
```

---

## 🟡 불필요한 데이터 로딩

**탐지 패턴**
```java
// ❌ 필요 없는 필드까지 전부 조회 (SELECT *)
List<User> users = userRepository.findAll();
return users.stream()
    .map(u -> new UserSummary(u.getId(), u.getName()))
    .toList();

// ❌ 엔티티 수정 목적 없이 조회 후 DTO 변환
User user = userRepository.findByIdWithAllRelations(id);
return UserDetailDto.from(user);
```

**개선 코드**
```java
// ✅ Projections — 필요한 필드만 조회
public interface UserSummaryProjection {
    Long getId();
    String getName();
}
List<UserSummaryProjection> findAllProjectedBy();

// ✅ QueryDSL Projections.constructor
List<UserSummaryDto> result = queryFactory
    .select(Projections.constructor(UserSummaryDto.class,
        user.id, user.name))
    .from(user)
    .fetch();
```

---

## 🟡 동기 처리 → 비동기 개선

**탐지 패턴**
```java
// ❌ 이메일 발송이 API 응답을 블로킹
public OrderResponse placeOrder(PlaceOrderCommand command) {
    Order order = orderService.place(command);
    emailService.sendConfirmation(order);  // 이메일 발송 대기
    smsService.sendConfirmation(order);    // SMS 발송 대기
    return OrderResponse.from(order);      // 전부 완료 후 응답
}
```

**개선 코드**
```java
// ✅ 비동기 이벤트 기반 처리
public OrderResponse placeOrder(PlaceOrderCommand command) {
    Order order = orderService.place(command);
    // 이벤트만 발행 → 핸들러에서 비동기 처리
    return OrderResponse.from(order);  // 즉시 응답
}

@TransactionalEventListener(phase = AFTER_COMMIT)
@Async  // 별도 스레드에서 실행
public void handleOrderPlaced(OrderPlacedEvent event) {
    emailService.sendConfirmation(event.orderId());
    smsService.sendConfirmation(event.orderId());
}
```

---

## 🟢 불필요한 스트림 다중 순회

**탐지 패턴**
```java
// ❌ 같은 컬렉션을 여러 번 순회
long count = orders.stream().filter(o -> o.isPending()).count();
List<Order> pending = orders.stream().filter(o -> o.isPending()).toList();
BigDecimal total = orders.stream().filter(o -> o.isPending())
    .map(Order::getAmount).reduce(BigDecimal.ZERO, BigDecimal::add);
```

**개선 코드**
```java
// ✅ 한 번만 순회
Map<Boolean, List<Order>> partitioned = orders.stream()
    .collect(Collectors.partitioningBy(Order::isPending));
List<Order> pending = partitioned.get(true);
long count = pending.size();
BigDecimal total = pending.stream()
    .map(Order::getAmount).reduce(BigDecimal.ZERO, BigDecimal::add);
```

---

## React 성능 체크리스트

```tsx
// ❌ 렌더링마다 새 객체/함수 생성 → 불필요한 리렌더
<UserList
  filters={{ page: 0, size: 10 }}   // 매 렌더마다 새 객체
  onDelete={() => handleDelete()}    // 매 렌더마다 새 함수
/>

// ✅ useMemo / useCallback으로 안정화
const filters = useMemo(() => ({ page, size: 10 }), [page]);
const handleDelete = useCallback((id) => deleteUser(id), [deleteUser]);

// ❌ 대용량 리스트 렌더링 (가상화 미사용)
{thousandItems.map(item => <Item key={item.id} {...item} />)}

// ✅ React Virtual로 가상화
import { useVirtualizer } from '@tanstack/react-virtual';
```
