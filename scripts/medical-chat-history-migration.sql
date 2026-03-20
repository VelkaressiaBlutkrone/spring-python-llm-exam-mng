-- MedicalHistory / ChatHistory 분리 마이그레이션
-- 실행: docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db < scripts/medical-chat-history-migration.sql
--
-- ERD v4.0 정합: chat_history → chatbot_history (병원 규칙 Q&A)
-- MedicalHistory(의학 질의)는 별도 테이블
--
-- 참고: Hibernate ddl-auto: update는 신규 테이블만 생성하고,
--       기존 테이블명 변경은 수행하지 않으므로 수동 마이그레이션 필요.

USE llm_db;

-- 1. chat_history → chatbot_history 테이블명 변경 (ERD v4.0 정합)
-- 기존 chat_history 테이블이 있는 경우에만 실행
-- chatbot_history가 이미 존재하면 이 단계는 건너뛰세요.
RENAME TABLE chat_history TO chatbot_history;

-- 2. chatbot_history 스키마 보정 (created_at 누락 시)
ALTER TABLE chatbot_history ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT NOW();

-- 3. medical_history 테이블은 Hibernate ddl-auto:update로 자동 생성됨
-- 수동 생성이 필요한 경우:
-- CREATE TABLE IF NOT EXISTS medical_history (
--     id BIGINT NOT NULL AUTO_INCREMENT,
--     staff_id BIGINT,
--     question TEXT NOT NULL,
--     answer TEXT NOT NULL,
--     status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
--     created_at DATETIME NOT NULL DEFAULT NOW(),
--     PRIMARY KEY (id),
--     CONSTRAINT fk_medical_history_staff FOREIGN KEY (staff_id) REFERENCES staff(id)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
