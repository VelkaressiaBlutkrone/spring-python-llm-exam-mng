# 설계 원칙 리뷰 체크리스트

---

## 설계 체크리스트

```
□ SRP: 클래스/함수가 하나의 책임만 갖는가?
□ OCP: 기능 추가 시 기존 코드 수정 없이 확장 가능한가?
□ DIP: 고수준 모듈이 저수준 구현에 직접 의존하지 않는가?
□ 순환 의존성: 패키지/모듈 간 순환 참조가 없는가?
□ 트랜잭션 경계: 하나의 트랜잭션이 너무 많은 책임을 갖지 않는가?
□ 예외 처리: 비즈니스 예외와 시스템 예외를 구분하는가?
□ 의도 명확성: 메서드/클래스 이름만 보고 역할을 알 수 있는가?
```

---

## 🟡 SRP 위반 (단일 책임 원칙)

**탐지 패턴**
```java
// ❌ UserService가 너무 많은 책임
@Service
public class UserService {
    // 사용자 CRUD (✓ 맞음)
    public UserResponse getUser(Long id) { ... }
    public UserResponse createUser(UserRequest req) { ... }

    // 이메일 발송 (✗ 별도 서비스 책임)
    public void sendWelcomeEmail(User user) { ... }

    // JWT 토큰 생성 (✗ 인증 서비스 책임)
    public String generateToken(User user) { ... }

    // 통계 집계 (✗ 분석 서비스 책임)
    public UserStats calculateStats(Long userId) { ... }

    // 파일 업로드 (✗ 파일 서비스 책임)
    public String uploadAvatar(MultipartFile file) { ... }
}
```

**개선 코드**
```java
// ✅ 책임 분리
@Service public class UserService { ... }         // CRUD만
@Service public class UserAuthService { ... }     // 인증/토큰
@Service public class UserNotificationService { } // 알림
@Service public class UserStatisticsService { }   // 통계
@Service public class UserFileService { ... }     // 파일
```

**PR 코멘트**
```
🟡 **[Major] SRP 위반 — UserService 과다한 책임**
UserService가 CRUD 외에 이메일, JWT, 통계, 파일 업로드까지 담당합니다.
각 책임을 독립 서비스로 분리하면 테스트와 유지보수가 쉬워집니다.
```

---

## 🟡 OCP 위반 (개방-폐쇄 원칙)

**탐지 패턴**
```java
// ❌ 새 결제 수단 추가 시마다 기존 코드 수정 필요
public class PaymentService {
    public void pay(String method, BigDecimal amount) {
        if (method.equals("CARD")) {
            cardPayment.process(amount);
        } else if (method.equals("KAKAO")) {
            kakaoPayment.process(amount);
        } else if (method.equals("NAVER")) {   // 추가할 때마다 수정
            naverPayment.process(amount);
        }
    }
}
```

**개선 코드**
```java
// ✅ Strategy Pattern — 새 전략 추가만으로 확장
public interface PaymentStrategy {
    boolean supports(PaymentMethod method);
    void process(BigDecimal amount);
}

@Component
public class CardPaymentStrategy implements PaymentStrategy {
    @Override public boolean supports(PaymentMethod method) {
        return method == PaymentMethod.CARD;
    }
    @Override public void process(BigDecimal amount) { ... }
}

// 새 결제 수단 추가 = 새 클래스 추가만으로 완료
@Component
public class KakaoPaymentStrategy implements PaymentStrategy { ... }

@Service
@RequiredArgsConstructor
public class PaymentService {
    private final List<PaymentStrategy> strategies;  // 자동 주입

    public void pay(PaymentMethod method, BigDecimal amount) {
        strategies.stream()
            .filter(s -> s.supports(method))
            .findFirst()
            .orElseThrow(() -> new BusinessException(ErrorCode.UNSUPPORTED_PAYMENT))
            .process(amount);
    }
}
```

---

## 🟡 DIP 위반 (의존성 역전 원칙)

**탐지 패턴**
```java
// ❌ 고수준 모듈이 저수준 구현에 직접 의존
@Service
public class OrderService {
    // 인터페이스 없이 구체 클래스에 직접 의존
    private final MySQLOrderRepository orderRepository;
    private final AwsS3FileService fileService;
    private final NaverSmsService smsService;
}
```

**개선 코드**
```java
// ✅ 인터페이스(포트)에 의존
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;    // 인터페이스
    private final FileStoragePort fileStorage;        // 포트
    private final NotificationPort notification;      // 포트
    // 구현 교체 시 OrderService 코드 변경 불필요
}
```

---

## 🟡 트랜잭션 경계 문제

**탐지 패턴**
```java
// ❌ 트랜잭션 내에서 외부 API 호출 → 장시간 트랜잭션 점유
@Transactional
public OrderResponse placeOrder(PlaceOrderCommand command) {
    Order order = Order.place(command);
    orderRepository.save(order);

    // 외부 결제 API 호출 (수 초 소요 가능) → 트랜잭션 길어짐
    PaymentResult result = paymentGateway.charge(order.getTotal());

    // 외부 재고 API 호출
    inventoryClient.decrease(command.items());

    return OrderResponse.from(order);
}
```

**개선 코드**
```java
// ✅ 트랜잭션 최소화 + 도메인 이벤트로 외부 통신 분리
@Transactional
public Long placeOrder(PlaceOrderCommand command) {
    Order order = Order.place(command);
    orderRepository.save(order);
    // 이벤트만 등록 — 외부 API는 트랜잭션 밖에서
    return order.getId();
}

@TransactionalEventListener(phase = AFTER_COMMIT)
@Async
public void handleOrderPlaced(OrderPlacedEvent event) {
    // 트랜잭션 외부에서 외부 API 호출
    paymentGateway.charge(event.orderId());
}
```

---

## 🟡 예외 처리 안티패턴

**탐지 패턴**
```java
// ❌ 예외 무시 (Swallow Exception)
try {
    sendEmail(user.getEmail());
} catch (Exception e) {
    // 아무것도 안 함 → 문제 숨김
}

// ❌ 너무 넓은 예외 잡기
try {
    processOrder(command);
} catch (Exception e) {   // NullPointerException, OutOfMemoryError도 잡힘
    return ResponseEntity.badRequest().build();
}

// ❌ 예외를 로그 후 다시 던지기 (중복 로깅)
try {
    ...
} catch (BusinessException e) {
    log.error("에러 발생", e);   // 여기서 로그
    throw e;                      // GlobalExceptionHandler에서 또 로그
}
```

**개선 코드**
```java
// ✅ 예외 처리 or 전파 중 하나만 선택
try {
    sendEmail(user.getEmail());
} catch (EmailSendException e) {
    log.warn("이메일 발송 실패: userId={}", user.getId(), e);
    // 실패해도 주문 처리는 계속 (비중요 작업)
}

// ✅ 구체적인 예외만 잡기
catch (BusinessException e) {
    throw e;  // 비즈니스 예외는 GlobalExceptionHandler로
} catch (DataAccessException e) {
    throw new BusinessException(ErrorCode.DATABASE_ERROR, e);
}

// ✅ 로그는 GlobalExceptionHandler 한 곳에서만
@ExceptionHandler(BusinessException.class)
public ResponseEntity<?> handle(BusinessException e) {
    log.warn("BusinessException: {}", e.getMessage());  // 한 곳에서만
    return ...;
}
```

---

## 🟢 불명확한 의도 (네이밍)

**탐지 패턴**
```java
// ❌ 의미 불명확한 이름
public List<User> getUsers(String s, int t, boolean f) { ... }
public void proc(Order o) { ... }
int x = calculate(a, b);
```

**개선 코드**
```java
// ✅ 의도가 드러나는 이름
public Page<User> searchUsersByKeyword(
        String keyword,
        int pageNumber,
        boolean includeInactive) { ... }

public void confirmOrder(Order order) { ... }

int totalPrice = calculateTotalPrice(basePrice, discountRate);
```

---

## React/TypeScript 설계 체크리스트

```tsx
// ❌ 거대 컴포넌트 (200줄+, props 10개+)
function DashboardPage({ user, orders, stats, settings, ... }) { }

// ✅ 컴포넌트 분리 + 커스텀 훅으로 로직 분리
function DashboardPage() {
  const { user } = useAuthStore();
  return (
    <div>
      <UserProfile userId={user.id} />   // 데이터 직접 fetch
      <OrderSummary userId={user.id} />
      <StatsWidget userId={user.id} />
    </div>
  );
}

// ❌ useEffect 남용 (파생 상태를 effect로 동기화)
const [fullName, setFullName] = useState('');
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);

// ✅ useMemo 또는 계산 값으로 표현
const fullName = useMemo(
  () => `${firstName} ${lastName}`,
  [firstName, lastName]
);
// 또는 그냥 const fullName = `${firstName} ${lastName}`;
```
