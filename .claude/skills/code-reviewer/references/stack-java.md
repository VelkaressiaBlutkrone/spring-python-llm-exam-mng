# Java / Spring Boot 전용 체크리스트

```
□ @Transactional 누락 (쓰기 작업)
□ @Transactional(readOnly=true) 누락 (읽기 작업)
□ LazyInitializationException 가능성
□ 생성자 주입 대신 필드/Setter 주입
□ Optional.get() 직접 호출 (NoSuchElementException 위험)
□ 엔티티를 API 응답으로 직접 반환
□ @Builder + @NoArgsConstructor 충돌
□ equals/hashCode 미구현 (Entity, VO)
□ 복잡한 생성자 대신 정적 팩토리 메서드 미사용
```

### 🟡 @Transactional 누락

```java
// ❌ 쓰기 작업에 @Transactional 없음
public void updateUser(Long id, UserRequest req) {
    User user = userRepository.findById(id).orElseThrow();
    user.update(req);  // 영속성 컨텍스트 없어 업데이트 안 될 수 있음
}

// ✅
@Transactional
public void updateUser(Long id, UserRequest req) { ... }

// ❌ 조회에 readOnly=false (기본값) — 스냅샷 생성 낭비
@Transactional
public UserResponse getUser(Long id) { ... }

// ✅
@Transactional(readOnly = true)
public UserResponse getUser(Long id) { ... }
```

### 🟡 필드 주입 사용

```java
// ❌ 필드 주입 — 순환 의존성 감지 불가, 테스트 어려움
@Service
public class UserService {
    @Autowired
    private UserRepository userRepository;
}

// ✅ 생성자 주입 (final + @RequiredArgsConstructor)
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;
}
```

### 🟡 Optional.get() 직접 호출

```java
// ❌ NoSuchElementException 위험
User user = userRepository.findById(id).get();

// ✅ 명시적 예외 처리
User user = userRepository.findById(id)
    .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

// ✅ 없을 수 있는 경우 처리
Optional<User> user = userRepository.findById(id);
user.ifPresent(u -> sendNotification(u));
```

### 🟡 Entity API 직접 노출

```java
// ❌ Entity를 Response로 직접 반환
@GetMapping("/{id}")
public User getUser(@PathVariable Long id) {
    return userRepository.findById(id).orElseThrow();
    // 순환 참조, 비밀번호 노출, 도메인 모델 변경 시 API 변경
}

// ✅ DTO로 변환
@GetMapping("/{id}")
public UserResponse getUser(@PathVariable Long id) {
    return UserResponse.from(userRepository.findById(id).orElseThrow());
}
```
