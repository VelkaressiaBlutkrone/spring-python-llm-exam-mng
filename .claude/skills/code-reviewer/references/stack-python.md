# Python / FastAPI 전용 체크리스트

```
□ Depends 인증 누락 (엔드포인트에 인증 의존성 미적용)
□ sync 함수에서 DB 호출 (async def 대신 def로 블로킹 I/O)
□ Pydantic 스키마 미사용 (dict 직접 반환 대신 response_model 권장)
□ 예외 핸들러 미등록 (HTTPException만 사용, 커스텀 핸들러 없음)
```

| 심각도 | 항목 | 설명 |
|--------|------|------|
| 🔴 | Depends 인증 누락 | 엔드포인트에 인증 의존성 미적용 |
| 🟡 | sync 함수에서 DB 호출 | async def 대신 def로 블로킹 I/O |
| 🟡 | Pydantic 스키마 미사용 | dict 직접 반환 대신 response_model 권장 |
| 🟡 | 예외 핸들러 미등록 | HTTPException만 사용, 커스텀 핸들러 없음 |

### 🔴 Depends 인증 누락

```python
# ❌ 인증 없이 모든 요청 허용
@router.get("/admin/users")
async def get_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# ✅ 인증 의존성 주입
@router.get("/admin/users")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),  # 인증 + 권한 검사
):
    return db.query(User).all()
```

### 🟡 sync 함수에서 DB 호출

```python
# ❌ def 함수에서 블로킹 I/O — 이벤트 루프 차단
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()

# ✅ async def 사용 (비동기 DB 드라이버와 함께)
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# ✅ 동기 드라이버 유지 시 run_in_executor로 스레드 풀 위임
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: db.query(User).filter(User.id == user_id).first())
```

### 🟡 Pydantic 스키마 미사용

```python
# ❌ dict 직접 반환 — 응답 구조 보장 없음, 민감 필드 노출 가능
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    user = await db.get(User, user_id)
    return {"id": user.id, "email": user.email, "password": user.password}  # 패스워드 노출!

# ✅ response_model로 응답 스키마 명시
class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    model_config = ConfigDict(from_attributes=True)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    user = await db.get(User, user_id)
    return user  # Pydantic이 자동 직렬화 + 민감 필드 제외
```

### 🟡 예외 핸들러 미등록

```python
# ❌ HTTPException만 사용 — 비즈니스 예외가 500으로 노출됨
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_async_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(user)
    # DB 오류 발생 시 500 Internal Server Error → 스택 트레이스 노출 가능

# ✅ 커스텀 예외 + 전역 핸들러 등록
class BusinessException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# main.py
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )

# 사용
raise BusinessException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다", status_code=404)
```
