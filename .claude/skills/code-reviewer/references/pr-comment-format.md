# PR 리뷰 코멘트 형식 가이드

---

## 코멘트 레벨 접두사

```
🔴 [Critical] — 머지 전 필수 수정
🟡 [Major]    — 수정 강력 권고
🟢 [Minor]    — 선택적 개선
💬 [Nitpick]  — 취향 차이, 강요 아님
❓ [Question] — 의도 확인 필요
✅ [Praise]   — 잘된 부분 칭찬
```

## 코멘트 작성 원칙

```
1. 문제 + 이유 + 대안 세트로 작성
2. 명령형이 아닌 제안형 ("~하면 어떨까요?")
3. 코드 스니펫 첨부로 구체적 개선 방향 제시
4. 칭찬도 명시 (좋은 점은 좋다고)
```

## 코멘트 템플릿

```markdown
<!-- Critical 예시 -->
🔴 **[Critical] SQL Injection 취약점**

문자열 연결로 쿼리를 구성하면 악의적인 입력으로 DB 전체가 노출될 수 있습니다.

```java
// Before
String query = "SELECT * FROM users WHERE email = '" + email + "'";

// After
Optional<User> findByEmail(String email);  // Spring Data JPA 파라미터 바인딩
```

<!-- Major 예시 -->
🟡 **[Major] N+1 쿼리 발생 가능성**

`order.getItems()` 호출 시 주문 수만큼 추가 쿼리가 발생합니다.
현재는 데이터가 적어 문제없지만, 트래픽 증가 시 성능 저하가 예상됩니다.

```java
// Fetch Join으로 개선
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.id = :id")
Optional<Order> findByIdWithItems(@Param("id") Long id);
```

<!-- Minor 예시 -->
🟢 **[Minor] 매직 넘버 상수화**

`5`의 의미가 코드에서 바로 파악되지 않습니다.

```java
private static final int MAX_LOGIN_ATTEMPTS = 5;
if (failCount >= MAX_LOGIN_ATTEMPTS) { ... }
```

<!-- Question 예시 -->
❓ **[Question] 의도 확인**

`includeDeleted` 파라미터가 기본값 `true`인데,
삭제된 데이터를 기본으로 포함하는 게 의도된 동작인가요?
일반적으로 기본값은 `false`가 더 안전할 것 같습니다.

<!-- Praise 예시 -->
✅ **[Praise] 도메인 로직 위치 👍**

비즈니스 규칙이 Service가 아닌 Order 엔티티 안에 잘 정의되어 있네요.
`order.cancel()` 내부에서 상태 검증까지 처리하는 패턴이 깔끔합니다.
```

---

## 전체 PR 리뷰 출력 예시

```markdown
## 📊 코드 리뷰 요약
- 🔴 Critical: 1건 (SQL Injection)
- 🟡 Major: 2건 (N+1, 트랜잭션 경계)
- 🟢 Minor: 3건 (네이밍, 매직 넘버, 주석)
- ✅ 잘된 점: 2건

---

## 🔴 Critical

### [L42] SQL Injection 취약점
...

## 🟡 Major

### [L78] N+1 쿼리
...

### [L95] 과도한 트랜잭션 범위
...

## 🟢 Minor

### [L15] 변수명 불명확
...

## ✅ 잘된 점

- Order 엔티티에 비즈니스 규칙이 잘 캡슐화되어 있습니다
- 에러 코드가 Enum으로 체계적으로 관리되고 있습니다

---
*Critical 1건 수정 후 머지 가능합니다.*
```
