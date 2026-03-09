package com.sample.llm.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
public class MedicalLlmResponse {

	private String generatedText;
	private String recommendedDepartment;
	private String recommendationReason;
	private List<DoctorWithScheduleDto> doctors;
}
