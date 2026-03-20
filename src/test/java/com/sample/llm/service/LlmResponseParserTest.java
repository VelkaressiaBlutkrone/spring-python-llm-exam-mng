package com.sample.llm.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class LlmResponseParserTest {

	private final LlmResponseParser parser = new LlmResponseParser();

	@Test
	@DisplayName("마크다운 볼드 형식에서 진료과 추출")
	void extractDepartment_markdownBold() {
		String response = "**추천 진료과**: 정형외과\n\n무릎 통증이 심하다면...";
		assertThat(parser.extractDepartment(response)).isEqualTo("정형외과");
	}

	@Test
	@DisplayName("일반 텍스트 형식에서 진료과 추출")
	void extractDepartment_plainText() {
		String response = "추천 진료과: 신경과\n두통 증상은...";
		assertThat(parser.extractDepartment(response)).isEqualTo("신경과");
	}

	@Test
	@DisplayName("전각 콜론 형식에서 진료과 추출")
	void extractDepartment_fullWidthColon() {
		String response = "추천 진료과： 내과\n소화 불량 증상...";
		assertThat(parser.extractDepartment(response)).isEqualTo("내과");
	}

	@Test
	@DisplayName("진료과 추출 실패 시 null 반환")
	void extractDepartment_notFound() {
		String response = "일반적인 답변입니다. 병원에 가세요.";
		assertThat(parser.extractDepartment(response)).isNull();
	}

	@Test
	@DisplayName("null 입력 시 null 반환")
	void extractDepartment_null() {
		assertThat(parser.extractDepartment(null)).isNull();
	}

	@Test
	@DisplayName("빈 문자열 입력 시 null 반환")
	void extractDepartment_blank() {
		assertThat(parser.extractDepartment("  ")).isNull();
	}

	@Test
	@DisplayName("추천 이유 추출")
	void extractRecommendationReason() {
		String response = "**추천 진료과**: 정형외과\n무릎 통증이 걸을 때 심해지는 증상은 관절 문제를 의심할 수 있습니다.\n\n**응급 상황 판단**...";
		String reason = parser.extractRecommendationReason(response);
		assertThat(reason).contains("무릎 통증");
	}

	@Test
	@DisplayName("추천 이유 추출 실패 시 null 반환")
	void extractRecommendationReason_notFound() {
		String response = "일반 답변입니다.";
		assertThat(parser.extractRecommendationReason(response)).isNull();
	}
}
