-- ERD 문서 v4.0 정합 마이그레이션
-- 실행: docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db < scripts/erd-alignment-migration.sql
-- 또는: mysql -u llm_admin -p llm_db < scripts/erd-alignment-migration.sql

USE llm_db;

-- 1. users → staff 테이블명 변경
RENAME TABLE users TO staff;

-- 2. chat_history → chatbot_history 테이블명 변경
RENAME TABLE chat_history TO chatbot_history;

-- 3. chatbot_history 컬럼명 변경 (ERD 명칭)
ALTER TABLE chatbot_history
    CHANGE COLUMN user_id staff_id BIGINT NULL,
    CHANGE COLUMN query question TEXT NOT NULL,
    CHANGE COLUMN response answer TEXT NULL,
    CHANGE COLUMN timestamp created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- 4. staff 테이블에 employee_number 추가 (ERD 필수, 기존 데이터 호환을 위해 nullable)
-- 참고: 이미 존재 시 오류 발생. 수동 실행 시 해당 라인 주석 처리.
ALTER TABLE staff ADD COLUMN employee_number VARCHAR(20) NULL UNIQUE AFTER username;
