package com.sample.llm.dto;

import com.sample.llm.entity.MedicalHistory;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class MedicalHistoryResponse {

	private Long id;
	private String sessionId;
	private String question;
	private String answer;
	private String status;
	private String metadata;
	private LocalDateTime createdAt;

	public static MedicalHistoryResponse from(MedicalHistory entity) {
		return new MedicalHistoryResponse(
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
