package com.sample.llm.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class LlmRequest {

	@NotBlank(message = "쿼리는 필수입니다")
	@Size(min = 1, max = 4096, message = "쿼리는 1~4096자 이내여야 합니다")
	private String query;
}
