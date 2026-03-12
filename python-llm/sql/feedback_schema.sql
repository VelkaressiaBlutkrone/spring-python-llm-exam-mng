-- 피드백 테이블 (medical_history에 추가 또는 별도 테이블)
CREATE TABLE IF NOT EXISTS llm_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) DEFAULT NULL COMMENT '세션 ID',
    query TEXT NOT NULL COMMENT '사용자 질문',
    response TEXT NOT NULL COMMENT 'LLM 응답',
    score INT NOT NULL COMMENT '만족도 (1-5)',
    comment TEXT DEFAULT NULL COMMENT '피드백 코멘트',
    endpoint VARCHAR(50) DEFAULT 'medical' COMMENT '사용 엔드포인트',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_score (score),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
