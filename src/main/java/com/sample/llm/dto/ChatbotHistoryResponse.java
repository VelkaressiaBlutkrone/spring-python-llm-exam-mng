package com.sample.llm.dto;

import com.sample.llm.entity.ChatbotHistory;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class ChatbotHistoryResponse {

	private Long id;
	private String sessionId;
	private String question;
	private String answer;
	private String status;
	private String metadata;
	private LocalDateTime createdAt;

	public static ChatbotHistoryResponse from(ChatbotHistory entity) {
		return new ChatbotHistoryResponse(
				entity.getId(),
				entity.getSessionId(),
				entity.getQuestion(),
				entity.getAnswer(),
				entity.getStatus(),
				entity.getMetadata(),
				entity.getCreatedAt()
		);
	}
}
