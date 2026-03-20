package com.sample.llm.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * LLM 응답 텍스트에서 추천 진료과명과 추천 이유를 추출하는 파서.
 * 시스템 프롬프트 규칙에 따라 "추천 진료과" 다음의 진료과명을 파싱한다.
 */
@Component
@Slf4j
public class LlmResponseParser {

	// "추천 진료과" 뒤에 오는 진료과명 추출
	// 예: "**추천 진료과**: 정형외과", "추천 진료과: 신경과"
	private static final Pattern DEPARTMENT_PATTERN = Pattern.compile(
			"추천\\s*진료과[*]*\\s*[:：]\\s*[*]*\\s*(.+?)\\s*[*]*\\s*$",
			Pattern.MULTILINE
	);

	// 추천 이유: 진료과 추출 라인 다음부터 첫 번째 빈 줄 또는 구분선까지
	private static final Pattern REASON_PATTERN = Pattern.compile(
			"추천\\s*진료과[*]*\\s*[:：].+?\\n+(.+?)(?=\\n\\s*\\n|\\n[-─*]{2,}|$)",
			Pattern.DOTALL
	);

	/**
	 * LLM 응답에서 추천 진료과명을 추출한다.
	 *
	 * @param llmResponse LLM 원본 응답 텍스트
	 * @return 추천 진료과명 (추출 실패 시 null)
	 */
	public String extractDepartment(String llmResponse) {
		if (llmResponse == null || llmResponse.isBlank()) {
			return null;
		}

		Matcher matcher = DEPARTMENT_PATTERN.matcher(llmResponse);
		if (matcher.find()) {
			String department = matcher.group(1)
					.replaceAll("[*]", "")
					.trim();
			log.info("Extracted department: {}", department);
			return department;
		}

		log.info("Could not extract department from LLM response");
		return null;
	}

	/**
	 * LLM 응답에서 추천 이유를 추출한다.
	 * 진료과 추천 라인 다음 문단을 추출한다.
	 *
	 * @param llmResponse LLM 원본 응답 텍스트
	 * @return 추천 이유 (추출 실패 시 null)
	 */
	public String extractRecommendationReason(String llmResponse) {
		if (llmResponse == null || llmResponse.isBlank()) {
			return null;
		}

		Matcher matcher = REASON_PATTERN.matcher(llmResponse);
		if (matcher.find()) {
			return matcher.group(1).trim();
		}

		return null;
	}
}
