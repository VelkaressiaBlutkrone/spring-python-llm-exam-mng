# SQL / QueryDSL 전용 체크리스트

```
□ SELECT * 사용 (불필요한 컬럼 조회)
□ WHERE 절 없는 UPDATE/DELETE
□ 인덱스 컬럼에 함수 적용 (인덱스 무력화)
□ IN 절 대량 ID 리스트 (1000개 이상)
□ BooleanExpression null 처리 누락
□ count 쿼리와 목록 쿼리 불일치
```

### 🔴 WHERE 없는 UPDATE/DELETE

```sql
-- ❌ 전체 데이터 업데이트 위험
UPDATE users SET status = 'INACTIVE';

-- ✅ 조건 명시
UPDATE users SET status = 'INACTIVE'
WHERE last_login_at < NOW() - INTERVAL 1 YEAR
  AND status = 'ACTIVE';
```

### 🟡 인덱스 컬럼에 함수 적용

```sql
-- ❌ created_at 인덱스 있어도 함수 적용으로 무력화
WHERE DATE(created_at) = '2024-01-15'
WHERE YEAR(created_at) = 2024

-- ✅ 범위 조건으로 인덱스 활용
WHERE created_at >= '2024-01-15 00:00:00'
  AND created_at < '2024-01-16 00:00:00'
```

### 🟡 QueryDSL BooleanExpression null 처리

```java
// ❌ null 조건이 NPE 유발 가능
.where(
    condition.getStatus() != null
        ? order.status.eq(condition.getStatus())
        : null,
    order.amount.goe(condition.getMinAmount())  // getMinAmount()가 null이면 NPE
)

// ✅ null-safe BooleanExpression 헬퍼
private BooleanExpression statusEq(OrderStatus status) {
    return status != null ? order.status.eq(status) : null;
}

private BooleanExpression amountGoe(Integer minAmount) {
    return minAmount != null ? order.amount.goe(minAmount) : null;
}

.where(statusEq(condition.getStatus()), amountGoe(condition.getMinAmount()))
```
