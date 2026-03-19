# TypeScript / React 전용 체크리스트

```
□ any 타입 남용
□ non-null assertion (!) 남용
□ useEffect 의존성 배열 누락 / 과잉
□ 컴포넌트 내부에서 또 다른 컴포넌트 정의
□ key prop에 index 사용 (동적 리스트)
□ 이벤트 핸들러에서 직접 비동기 처리 누락
□ 상태 업데이트 배칭 미고려
```

### 🟡 any 타입 남용

```typescript
// ❌ any → 타입 안전성 제거
function processData(data: any) {
    return data.user.name;  // 런타임 에러 가능
}

// ✅ 명시적 타입 또는 unknown + 타입 가드
function processData(data: unknown) {
    if (!isUserData(data)) throw new Error('Invalid data');
    return data.user.name;
}

function isUserData(data: unknown): data is UserData {
    return typeof data === 'object' && data !== null && 'user' in data;
}
```

### 🟡 useEffect 의존성 누락

```tsx
// ❌ userId 변경 시 재실행 안 됨
useEffect(() => {
    fetchUser(userId);
}, []);  // userId 누락

// ✅
useEffect(() => {
    fetchUser(userId);
}, [userId]);  // 의존성 명시

// ❌ 함수 참조가 계속 변해 무한 루프
useEffect(() => {
    fetchData(filters);
}, [filters]);  // filters가 객체라면 매 렌더마다 새 참조

// ✅ useMemo로 참조 안정화
const stableFilters = useMemo(() => filters, [filters.page, filters.size]);
useEffect(() => { fetchData(stableFilters); }, [stableFilters]);
```

### 🟡 컴포넌트 내부 컴포넌트 정의

```tsx
// ❌ 렌더링마다 새 컴포넌트 생성 → 성능 저하 & state 초기화
function ParentComponent() {
    const InnerComponent = () => <div>내부</div>;  // 매 렌더마다 새 정의
    return <InnerComponent />;
}

// ✅ 컴포넌트 외부로 분리
const InnerComponent = () => <div>내부</div>;

function ParentComponent() {
    return <InnerComponent />;
}
```
