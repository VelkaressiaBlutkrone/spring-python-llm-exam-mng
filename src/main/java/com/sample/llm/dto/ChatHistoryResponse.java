package com.sample.llm.dto;

import com.sample.llm.entity.ChatHistory;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class ChatHistoryResponse {

	private Long id;
	private String sessionId;
	private String question;
	private String answer;
	private LocalDateTime createdAt;

	public static ChatHistoryResponse from(ChatHistory entity) {
		return new ChatHistoryResponse(
				entity.getId(),
				entity.getSessionId(),
				entity.getQuestion(),
				entity.getAnswer(),
				entity.getCreatedAt()
		);
	}
}
