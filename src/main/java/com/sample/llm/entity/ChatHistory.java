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

@Entity
@Table(name = "chat_history")
@Getter
@Setter
@NoArgsConstructor
public class ChatHistory {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "user_id")
	private User user;

	@Column(name = "session_id", length = 64)
	private String sessionId;

	@Column(nullable = false, columnDefinition = "TEXT")
	private String query;

	@Column(columnDefinition = "TEXT")
	private String response;

	@Column(nullable = false, length = 20)
	private String status;  // PENDING, COMPLETED, FAILED

	@Column(columnDefinition = "TEXT")
	private String metadata;  // JSON: model, latency_ms, token_usage

	@Column(nullable = false)
	private LocalDateTime timestamp = LocalDateTime.now();

	public ChatHistory(String query, String status) {
		this.query = query;
		this.status = status;
	}

	public Long getUserId() {
		return user != null ? user.getId() : null;
	}
}
