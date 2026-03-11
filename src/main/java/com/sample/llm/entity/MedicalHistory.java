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
 * 의학/질병 관련 LLM 질의응답 이력.
 * 증상 추천, 진료과 추천 등 의료 상담 대화를 저장합니다.
 */
@Entity
@Table(name = "medical_history")
@Getter
@Setter
@NoArgsConstructor
public class MedicalHistory {

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
	private String status;  // PENDING, COMPLETED, FAILED

	@Column(columnDefinition = "TEXT")
	private String metadata;  // JSON: model, latency_ms, token_usage

	@Column(name = "created_at", nullable = false)
	private LocalDateTime createdAt = LocalDateTime.now();

	public MedicalHistory(String question, String status) {
		this.question = question;
		this.status = status;
	}

	public Long getStaffId() {
		return staff != null ? staff.getId() : null;
	}
}
