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
	private String query;
	private String response;
	private String status;
	private String metadata;
	private LocalDateTime timestamp;

	public static ChatHistoryResponse from(ChatHistory entity) {
		return new ChatHistoryResponse(
				entity.getId(),
				entity.getSessionId(),
				entity.getQuery(),
				entity.getResponse(),
				entity.getStatus(),
				entity.getMetadata(),
				entity.getTimestamp()
		);
	}
}
