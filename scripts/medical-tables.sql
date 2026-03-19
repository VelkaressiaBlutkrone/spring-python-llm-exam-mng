-- 의학지식 데이터 테이블 DDL
-- PowerShell: Get-Content scripts/medical-tables.sql -Raw | docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db
-- CMD/Bash:   docker exec -i llm-db mysql -uroot -prootpassword --default-character-set=utf8mb4 llm_db < scripts/medical-tables.sql

USE llm_db;

-- 1. domain 매핑 테이블 (참조용)
CREATE TABLE IF NOT EXISTS medical_domain (
    domain_id   INT PRIMARY KEY,
    domain_name VARCHAR(50) NOT NULL COMMENT '진료과/도메인명',

    UNIQUE INDEX idx_name (domain_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 초기 데이터
INSERT IGNORE INTO medical_domain (domain_id, domain_name) VALUES
(1, '영상의학과'), (2, '내과'), (3, '외과'), (4, '마취통증의학과'),
(5, '비뇨의학과'), (6, '안과'), (7, '신경과'), (8, '신경외과'),
(9, '종양내과'), (10, '병리과'), (11, '산부인과'),
(12, '이비인후과'), (13, '정신건강의학과'), (14, '피부과'),
(15, '예방의학'), (16, '의료법규'), (17, '소아청소년과'), (18, '응급의학과'),
(19, '정형외과');

-- 2. 원천데이터 (의학 지식 콘텐츠)
CREATE TABLE IF NOT EXISTS medical_content (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    c_id          VARCHAR(50)  NOT NULL COMMENT '원본 콘텐츠 ID',
    domain        INT          NOT NULL COMMENT '도메인 번호',
    source        INT          NULL     COMMENT '소스 유형 번호',
    source_spec   VARCHAR(255) NULL     COMMENT '소스 상세 (학회명, 교과서명 등)',
    creation_year VARCHAR(10)  NULL     COMMENT '생성 연도',
    content       LONGTEXT     NOT NULL COMMENT '의학 지식 원문',
    dataset       VARCHAR(20)  NOT NULL COMMENT '데이터셋 구분 (08_전문 / 09_필수의료)',
    data_type     VARCHAR(20)  NOT NULL DEFAULT 'training' COMMENT 'training / validation',
    language      VARCHAR(10)  NOT NULL DEFAULT 'ko' COMMENT '언어 (ko / en)',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_domain (domain),
    INDEX idx_dataset (dataset),
    INDEX idx_language (language),
    FULLTEXT INDEX ft_content (content) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 라벨링 Q&A 데이터
CREATE TABLE IF NOT EXISTS medical_qa (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    qa_id       INT          NOT NULL COMMENT '원본 Q&A ID',
    domain      INT          NOT NULL COMMENT '도메인 번호',
    department  VARCHAR(50)  NOT NULL COMMENT '진료과명 (내과, 외과 등)',
    q_type      INT          NOT NULL COMMENT '질문 유형 (1:객관식, 2:단답형, 3:서술형)',
    question    TEXT         NOT NULL COMMENT '질문',
    answer      TEXT         NOT NULL COMMENT '답변',
    dataset     VARCHAR(20)  NOT NULL COMMENT '데이터셋 구분 (08_전문 / 09_필수의료)',
    data_type   VARCHAR(20)  NOT NULL DEFAULT 'training' COMMENT 'training / validation',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_domain (domain),
    INDEX idx_department (department),
    INDEX idx_q_type (q_type),
    INDEX idx_dataset (dataset),
    FULLTEXT INDEX ft_question (question) WITH PARSER ngram,
    FULLTEXT INDEX ft_answer (answer) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 병원 규칙 (index_rule_data.py에서 medical_rules.json 적재)
CREATE TABLE IF NOT EXISTS medical_rule (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    category    VARCHAR(50)  NOT NULL,
    title       VARCHAR(200) NOT NULL,
    content     LONGTEXT     NOT NULL,
    target      VARCHAR(100) NULL,
    start_date  DATE         NULL,
    end_date    DATE         NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 예약 테이블
CREATE TABLE IF NOT EXISTS reservation_tb (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id        BIGINT       NOT NULL COMMENT '의사 FK',
    staff_id         BIGINT       NULL     COMMENT '직원 FK (nullable)',
    reservation_date DATE         NOT NULL COMMENT '예약 날짜',
    start_time       TIME         NOT NULL COMMENT '시작 시간',
    end_time         TIME         NOT NULL COMMENT '종료 시간',
    status           VARCHAR(20)  NOT NULL DEFAULT 'CONFIRMED' COMMENT '상태 (CONFIRMED, CANCELLED)',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_doctor_date (doctor_id, reservation_date),
    INDEX idx_staff (staff_id),
    CONSTRAINT fk_reservation_doctor FOREIGN KEY (doctor_id) REFERENCES doctor(id),
    CONSTRAINT fk_reservation_staff  FOREIGN KEY (staff_id)  REFERENCES staff(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
