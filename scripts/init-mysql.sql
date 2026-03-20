-- MySQL 초기 설정: 애플리케이션 전용 사용자 생성 및 권한 부여
-- Bash:  docker exec -i app-db mysql -uroot -p < scripts/init-mysql.sql
-- PowerShell:  .\scripts\run-mysql-init.ps1

CREATE DATABASE IF NOT EXISTS llm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- llm_admin (애플리케이션용 - 최소 권한)
-- 비밀번호는 docker-compose.yml의 MYSQL_PASSWORD 환경변수로 설정됨
-- docker-compose의 MYSQL_USER/MYSQL_PASSWORD로 자동 생성되므로
-- 아래는 수동 실행 시에만 사용

-- llm_admin에게 llm_db에 대한 권한만 부여 (전체 권한 아님)
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP
    ON llm_db.* TO 'llm_admin'@'%';

FLUSH PRIVILEGES;
