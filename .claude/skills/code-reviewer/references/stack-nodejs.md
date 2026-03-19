# Node.js / NestJS 전용 체크리스트

```
□ Guard 미적용 (컨트롤러에 인증/인가 Guard 없음)
□ ValidationPipe 미사용 (DTO 유효성 검증 없이 body 직접 사용)
□ 순환 의존성 (모듈 간 forwardRef로 순환 참조)
□ 에러 필터 미등록 (기본 에러 응답만 사용)
```

| 심각도 | 항목 | 설명 |
|--------|------|------|
| 🔴 | Guard 미적용 | 컨트롤러에 인증/인가 Guard 없음 |
| 🟡 | ValidationPipe 미사용 | DTO 유효성 검증 없이 body 직접 사용 |
| 🟡 | 순환 의존성 | 모듈 간 forwardRef로 순환 참조 |
| 🟡 | 에러 필터 미등록 | 기본 에러 응답만 사용 |

### 🔴 Guard 미적용

```typescript
// ❌ 인증 없이 모든 요청 허용
@Controller('admin/users')
export class AdminUserController {
    @Get()
    findAll() {
        return this.userService.findAll();
    }
}

// ✅ JwtAuthGuard + RolesGuard 적용
@Controller('admin/users')
@UseGuards(JwtAuthGuard, RolesGuard)  // 컨트롤러 레벨 전역 적용
export class AdminUserController {
    @Get()
    @Roles('ADMIN')  // 역할 기반 접근 제어
    findAll() {
        return this.userService.findAll();
    }
}
```

### 🟡 ValidationPipe 미사용

```typescript
// ❌ body를 any로 받아 유효성 검증 없음
@Post()
async createUser(@Body() body: any) {
    return this.userService.create(body.email, body.password);  // 잘못된 타입 그대로 전달
}

// ✅ DTO + class-validator로 자동 유효성 검증
export class CreateUserDto {
    @IsEmail()
    email: string;

    @IsString()
    @MinLength(8)
    password: string;
}

@Post()
async createUser(@Body() dto: CreateUserDto) {  // ValidationPipe가 자동 검증
    return this.userService.create(dto.email, dto.password);
}

// main.ts — 전역 ValidationPipe 등록
app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true }));
```

### 🟡 순환 의존성

```typescript
// ❌ UserModule ↔ OrderModule 순환 참조 — 앱 시작 실패 가능
@Module({
    imports: [OrderModule],  // UserModule이 OrderModule을 import
    providers: [UserService],
})
export class UserModule {}

@Module({
    imports: [UserModule],  // OrderModule도 UserModule을 import → 순환!
    providers: [OrderService],
})
export class OrderModule {}

// ✅ forwardRef로 순환 해소 (단기 해결책)
@Module({
    imports: [forwardRef(() => OrderModule)],
    providers: [UserService],
})
export class UserModule {}

// ✅ 근본 해결: 공통 의존성을 SharedModule로 분리
@Module({
    providers: [CommonService],
    exports: [CommonService],
})
export class SharedModule {}
```

### 🟡 에러 필터 미등록

```typescript
// ❌ 기본 NestJS 에러 응답 — 내부 상세 정보 노출 가능
throw new Error('DB connection failed');  // 500 + 스택 트레이스 유출 위험

// ✅ 커스텀 예외 필터 등록
@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
    catch(exception: unknown, host: ArgumentsHost) {
        const ctx = host.switchToHttp();
        const response = ctx.getResponse<Response>();

        const status = exception instanceof HttpException
            ? exception.getStatus()
            : HttpStatus.INTERNAL_SERVER_ERROR;

        const message = exception instanceof HttpException
            ? exception.message
            : '서버 오류가 발생했습니다';

        response.status(status).json({ statusCode: status, message });
    }
}

// main.ts
app.useGlobalFilters(new GlobalExceptionFilter());
```
