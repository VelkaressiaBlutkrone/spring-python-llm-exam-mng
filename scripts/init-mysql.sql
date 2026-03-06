-- MySQL 초기 설정: llm_user 생성 및 권한 부여
-- Bash:  docker exec -i app-db mysql -uroot -ppassword < scripts/init-mysql.sql
-- PowerShell:  .\scripts\run-mysql-init.ps1

CREATE DATABASE IF NOT EXISTS llm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- root@'%' 생성 (호스트에서 Docker MySQL 접속 시 172.18.0.1로 인식됨)
DROP USER IF EXISTS 'root'@'%';
CREATE USER 'root'@'%' IDENTIFIED BY 'rootpassword';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

-- llm_user (애플리케이션용)
DROP USER IF EXISTS 'llm_user'@'%';
DROP USER IF EXISTS 'llm_user'@'localhost';
CREATE USER 'llm_user'@'%' IDENTIFIED BY 'llm_user_1234';
GRANT ALL PRIVILEGES ON llm_db.* TO 'llm_user'@'%';

FLUSH PRIVILEGES;
