# 보안 리뷰 체크리스트

> 발견 즉시 🔴 Critical 또는 🟡 Major로 분류

---

## 공통 보안 체크리스트

```
□ 하드코딩된 시크릿 (비밀번호, API 키, JWT Secret)
□ 민감 정보 로그 출력 (카드번호, 비밀번호, 개인정보)
□ 입력값 검증 누락
□ 예외 메시지에 내부 구현 노출
□ 인증/인가 검사 누락
□ 경로 탐색 (Path Traversal) 취약점
```

---

## 🔴 SQL Injection

**탐지 패턴**
```java
// ❌ 문자열 연결로 쿼리 조합 → SQL Injection
String query = "SELECT * FROM users WHERE email = '" + email + "'";
em.createNativeQuery(query).getResultList();

// ❌ JPQL 문자열 연결도 동일하게 위험
String jpql = "SELECT u FROM User u WHERE u.name = '" + name + "'";
```

**개선 코드**
```java
// ✅ 파라미터 바인딩 사용
TypedQuery<User> query = em.createQuery(
    "SELECT u FROM User u WHERE u.email = :email", User.class);
query.setParameter("email", email);

// ✅ Spring Data JPA (자동 파라미터 바인딩)
Optional<User> findByEmail(String email);

// ✅ QueryDSL (타입 안전)
queryFactory.selectFrom(user)
    .where(user.email.eq(email))  // 자동 파라미터화
    .fetchOne();
```

**PR 코멘트**
```
🔴 **[Critical] SQL Injection 취약점**
문자열 연결로 쿼리를 구성하면 SQL Injection에 노출됩니다.
파라미터 바인딩 또는 QueryDSL 사용을 권장합니다.
```

---

## 🔴 하드코딩된 시크릿

**탐지 패턴**
```java
// ❌ 코드에 직접 시크릿 포함
private static final String JWT_SECRET = "mySecretKey123";
String password = "admin1234";
String apiKey = "sk-proj-xxxxxxxxxxxxx";
```

**개선 코드**
```java
// ✅ 환경변수 + @Value
@Value("${jwt.secret}")
private String jwtSecret;

// ✅ @ConfigurationProperties
@ConfigurationProperties("jwt")
public record JwtProperties(String secret, long expiration) {}
```

**PR 코멘트**
```
🔴 **[Critical] 하드코딩된 시크릿**
JWT 시크릿/비밀번호가 코드에 직접 포함되어 있습니다.
Git 이력에 영구 기록되므로 즉시 환경변수로 이전 후
Git 이력에서도 제거해야 합니다.
```

---

## 🔴 민감 정보 로그 출력

**탐지 패턴**
```java
// ❌ 비밀번호/카드번호/개인정보 로그
log.info("로그인 요청: email={}, password={}", email, password);
log.debug("결제 요청: cardNumber={}, cvv={}", cardNumber, cvv);
log.info("사용자 정보: {}", user.toString()); // toString에 비밀번호 포함 시
```

**개선 코드**
```java
// ✅ 민감 필드 제외
log.info("로그인 시도: email={}", email);  // 비밀번호 제외

// ✅ @ToString 제외 처리
@ToString(exclude = {"password", "cardNumber"})
public class User { ... }

// ✅ 마스킹 처리
log.info("결제 요청: card=****{}", cardNumber.substring(cardNumber.length() - 4));
```

---

## 🔴 인증/인가 누락

**탐지 패턴**
```java
// ❌ Security 설정에서 과도한 permitAll
.authorizeHttpRequests(auth -> auth
    .anyRequest().permitAll()   // 모든 요청 허용
)

// ❌ 소유자 검증 없는 수정
public void updateUser(Long userId, UserRequest req) {
    User user = userRepository.findById(userId).orElseThrow();
    user.update(req);  // 현재 로그인 사용자가 userId 소유자인지 확인 안 함
}
```

**개선 코드**
```java
// ✅ 소유자 검증 추가
public void updateUser(Long userId, UserRequest req, Long currentUserId) {
    User user = userRepository.findById(userId).orElseThrow();

    if (!user.isOwnedBy(currentUserId)) {
        throw new BusinessException(ErrorCode.FORBIDDEN);
    }
    user.update(req);
}

// ✅ @PreAuthorize 활용
@PreAuthorize("@userSecurity.isOwner(authentication, #userId)")
public void updateUser(@PathVariable Long userId, ...) { }
```

---

## 🟡 XSS (TypeScript/React)

**탐지 패턴**
```tsx
// ❌ dangerouslySetInnerHTML 직접 사용
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// ❌ innerHTML 직접 할당
element.innerHTML = userInput;
```

**개선 코드**
```tsx
// ✅ DOMPurify로 sanitize 후 사용
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{
  __html: DOMPurify.sanitize(userContent)
}} />

// ✅ 텍스트 콘텐츠는 React 기본 이스케이프 활용
<p>{userContent}</p>  // React가 자동 이스케이프
```

---

## 🟡 Mass Assignment (일괄 할당 취약점)

**탐지 패턴**
```java
// ❌ 요청 전체를 엔티티에 매핑 → role, admin 필드까지 변경 가능
public void updateUser(Long id, User requestBody) {
    User user = userRepository.findById(id).orElseThrow();
    BeanUtils.copyProperties(requestBody, user);  // 모든 필드 복사
}
```

**개선 코드**
```java
// ✅ 허용된 필드만 명시적으로 업데이트
public void updateUser(Long id, UserRequest.Update request) {
    User user = userRepository.findById(id).orElseThrow();
    user.updateProfile(request.nickname(), request.profileImage());
    // role, admin 등 민감 필드는 별도 관리자 API로
}
```

---

## 🟡 Path Traversal

**탐지 패턴**
```java
// ❌ 파일명 검증 없이 직접 사용
public Resource downloadFile(String filename) {
    Path filePath = Paths.get(uploadDir).resolve(filename);
    return new FileSystemResource(filePath);
    // filename = "../../etc/passwd" 가능
}
```

**개선 코드**
```java
// ✅ 경로 정규화 + 상위 디렉토리 탈출 방지
public Resource downloadFile(String filename) {
    Path uploadPath = Paths.get(uploadDir).toAbsolutePath().normalize();
    Path filePath = uploadPath.resolve(filename).normalize();

    // 허용된 디렉토리 내인지 검증
    if (!filePath.startsWith(uploadPath)) {
        throw new BusinessException(ErrorCode.INVALID_FILE_PATH);
    }

    // 파일 존재 여부 확인
    if (!Files.exists(filePath)) {
        throw new BusinessException(ErrorCode.FILE_NOT_FOUND);
    }

    return new FileSystemResource(filePath);
}
```

---

## 🟡 예외 메시지 내부 구현 노출

**탐지 패턴**
```java
// ❌ 스택 트레이스 / DB 정보 그대로 노출
catch (Exception e) {
    return ResponseEntity.status(500).body(e.getMessage());
    // "Table 'users' doesn't exist" 등 내부 정보 노출
}
```

**개선 코드**
```java
// ✅ 사용자용 메시지 / 내부 로그 분리
@ExceptionHandler(Exception.class)
public ResponseEntity<ApiResponse<Void>> handleException(Exception e) {
    log.error("Unhandled exception", e);  // 내부 로그에만 상세 기록
    return ResponseEntity.internalServerError()
        .body(ApiResponse.fail(500, "서버 오류가 발생했습니다"));  // 사용자용
}
```
