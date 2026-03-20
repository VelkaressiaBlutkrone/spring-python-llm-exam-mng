# 가독성 리뷰 & PR 코멘트 형식 가이드

---

## 가독성 체크리스트

```
□ 메서드 길이 50줄 초과
□ 중첩 깊이 3단계 이상
□ 매직 넘버/문자열 (의미 없는 리터럴)
□ 불명확한 변수/메서드 이름
□ 불필요한 주석 (코드가 설명하면 주석 불필요)
□ 죽은 코드 (주석 처리된 코드, 사용 안 하는 메서드)
□ 일관성 없는 네이밍 규칙
```

---

## 🟢 Early Return으로 중첩 줄이기

**탐지 패턴**
```java
// ❌ 깊은 중첩 (Pyramid of Doom)
public String processUser(Long userId) {
    if (userId != null) {
        User user = userRepository.findById(userId).orElse(null);
        if (user != null) {
            if (user.isActive()) {
                if (user.hasPermission()) {
                    return user.process();
                }
            }
        }
    }
    return null;
}
```

**개선 코드**
```java
// ✅ Early Return으로 평탄화
public String processUser(Long userId) {
    if (userId == null) return null;

    User user = userRepository.findById(userId)
        .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

    if (!user.isActive()) throw new BusinessException(ErrorCode.INACTIVE_USER);
    if (!user.hasPermission()) throw new BusinessException(ErrorCode.FORBIDDEN);

    return user.process();
}
```

---

## 🟢 매직 넘버/문자열 상수화

**탐지 패턴**
```java
// ❌ 숫자/문자열의 의미를 알 수 없음
if (failCount >= 5) { lockAccount(); }
Thread.sleep(30000);
if (status.equals("ACTIVE")) { ... }
return price * 0.1;
```

**개선 코드**
```java
// ✅ 의미 있는 이름으로 상수화
private static final int MAX_LOGIN_ATTEMPTS = 5;
private static final Duration LOCK_WAIT_DURATION = Duration.ofSeconds(30);
private static final double VAT_RATE = 0.1;

if (failCount >= MAX_LOGIN_ATTEMPTS) { lockAccount(); }
Thread.sleep(LOCK_WAIT_DURATION.toMillis());
if (status == UserStatus.ACTIVE) { ... }  // String 대신 Enum
return price * VAT_RATE;
```

---

## 🟢 불필요한 주석

**탐지 패턴**
```java
// ❌ 코드가 이미 설명하는 내용을 주석으로 반복
// 사용자를 찾는다
User user = userRepository.findById(userId);

// 사용자가 없으면 예외를 던진다
if (user == null) throw new UserNotFoundException();

// 주문을 생성한다
Order order = Order.create(user, items);
```

**개선 코드**
```java
// ✅ 주석 없이 코드 자체가 의도를 표현
User user = userRepository.findById(userId)
    .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

Order order = Order.place(CustomerId.of(user.getId()), items);

// ✅ 주석이 필요한 경우: "왜"를 설명 (What은 코드가 설명)
// PG사 API 응답이 초 단위라 ms로 변환 필요
long timeoutMs = pgApiTimeout * 1000;
```

---

## 🟢 죽은 코드

**탐지 패턴**
```java
// ❌ 주석 처리된 코드
// public void oldMethod() {
//     // ... 구 구현
// }

// ❌ 사용 안 하는 import
import java.util.LinkedList;    // 사용 안 함
import java.util.TreeMap;       // 사용 안 함

// ❌ 도달 불가능한 코드
public String getStatus() {
    return "ACTIVE";
    log.debug("상태 조회");  // ← return 이후 실행 불가
}
```

**개선 코드**
```java
// ✅ 삭제 — Git 이력에 남아있으므로 주석 처리 불필요
// 필요한 import만 유지 (IDE 자동 정리)
```



> PR 코멘트 형식 가이드는 `references/pr-comment-format.md`를 참조한다.
