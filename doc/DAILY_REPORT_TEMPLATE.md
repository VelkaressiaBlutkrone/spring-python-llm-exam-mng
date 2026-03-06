# 일일 회고 템플릿

| 항목 | 내용 |
| ---- | ---- |
| **What** | 오늘 무엇을 했는지 |
| **Why** | 왜 그것을 했는지 |
| **Problem** | 어떤 문제가 있었는지 |
| **Solution** | 어떻게 해결했는지 |
| **회고** | 느낀 점 |

---

## 내용 구성 예시

### What (오늘 무엇을 했는지)

- Spring Boot Step 1~5 진행 (프로젝트 생성, application.yml, User/ChatHistory 엔티티, WebClient/LlmService)
- .env 기반 설정 구성 (springboot3-dotenv)
- MySQL init 스크립트 작성 (PowerShell, app-db 컨테이너)
- MVP 필수 기능 표 정리 (MVP_FEATURES.md)

### Why (왜 그것을 했는지)

- TASK_SPRING.md 작업 단계 수행
- PRD, RULE_SPRING 규칙 준수
- 로컬 개발 환경 구축 및 DB 초기화 자동화

### Problem (어떤 문제가 있었는지)

1. **테스트 실패**: DataLoader가 H2 스키마 생성 전에 `userRepository.count()` 호출
2. **MySQL Access Denied**: root/llm_user가 172.18.0.1에서 접속 거부
3. **PowerShell 리다이렉션**: `<` 연산자 미지원
4. **mysql 옵션 파싱 오류**: `-llm_user`가 `-l` 옵션으로 해석됨
5. **비밀번호 특수문자**: `-e "source ..."` 전달 시 shell 해석 문제
6. **root@localhost 한정**: Docker MySQL의 root는 localhost만 허용, 호스트(172.18.0.1) 접속 불가

### Solution (어떻게 해결했는지)

1. DataLoader에 `@Profile("!test")` 적용
2. `docker cp` + `sh -c "mysql ... < /tmp/init-mysql.sql"` 방식으로 변경
3. `--password=` 형식 사용, 비밀번호를 작은따옴표로 감싸 sh 해석 방지
4. .env에서 MYSQL_ROOT_PASSWORD 로드, rootpassword 기본값
5. init-mysql.sql에 `root@'%'` 생성하여 호스트 접속 허용
6. application.yml 기본 계정을 root/rootpassword로 설정

### 회고 (느낀 점)

- Docker MySQL은 호스트 접속 시 `root@'%'` 등 원격 허용 사용자가 필요함
- PowerShell 환경에서는 bash 스타일 리다이렉션·옵션 사용에 주의
- .env 기반 설정으로 민감 정보 관리와 환경별 설정 분리가 수월해짐
