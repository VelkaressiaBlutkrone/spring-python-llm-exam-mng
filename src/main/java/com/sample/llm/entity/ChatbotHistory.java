package com.sample.llm.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

/**
 * ERD v4.0 CHATBOT_HISTORY 테이블 매핑.
 * 챗봇 대화 이력. question/answer/created_at은 ERD 명칭.
 * status, metadata는 확장 컬럼(LLM 처리 상태 추적).
 */
@Entity
@Table(name = "chatbot_history")
@Getter
@Setter
@NoArgsConstructor
public class ChatbotHistory {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "staff_id")
	private Staff staff;

	@Column(name = "session_id", length = 100)
	private String sessionId;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String question;

	@Column(columnDefinition = "TEXT")
	private String answer;

	@Column(nullable = false, length = 20)
	private String status;  // PENDING, COMPLETED, FAILED (ERD 확장)

	@Column(columnDefinition = "TEXT")
	private String metadata;  // JSON: model, latency_ms, token_usage (ERD 확장)

	@Column(name = "created_at", nullable = false)
	private LocalDateTime createdAt = LocalDateTime.now();

	public ChatbotHistory(String question, String status) {
		this.question = question;
		this.status = status;
	}

	public Long getStaffId() {
		return staff != null ? staff.getId() : null;
	}
}
