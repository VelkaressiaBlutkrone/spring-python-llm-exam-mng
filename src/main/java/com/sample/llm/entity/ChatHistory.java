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
 * 병원 규칙 Q&A 챗봇 대화 이력.
 * 의사·간호사가 병원 내부 규칙(당직, 물품, 위생 등)에 대해 질의응답할 때 사용합니다.
 */
@Entity
@Table(name = "chatbot_history")
@Getter
@Setter
@NoArgsConstructor
public class ChatHistory {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "staff_id", nullable = false)
	private Staff staff;

	@Column(name = "session_id", nullable = false, length = 100)
	private String sessionId;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String question;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String answer;

	@Column(name = "created_at", nullable = false)
	private LocalDateTime createdAt = LocalDateTime.now();

	public ChatHistory(Staff staff, String sessionId, String question, String answer) {
		this.staff = staff;
		this.sessionId = sessionId;
		this.question = question;
		this.answer = answer;
	}

	public Long getStaffId() {
		return staff != null ? staff.getId() : null;
	}
}
