package com.sample.llm.integration;

import com.sample.llm.entity.MedicalHistory;
import com.sample.llm.entity.Staff;
import com.sample.llm.repository.MedicalHistoryRepository;
import com.sample.llm.repository.StaffRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MedicalIntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private StaffRepository staffRepository;

	@Autowired
	private MedicalHistoryRepository medicalHistoryRepository;

	@Autowired
	private com.sample.llm.repository.ChatHistoryRepository chatHistoryRepository;

	@MockitoBean
	private WebClient llmWebClient;

	private Staff testStaff;

	@BeforeEach
	void setUp() {
		chatHistoryRepository.deleteAll();
		medicalHistoryRepository.deleteAll();
		staffRepository.deleteAll();
		testStaff = staffRepository.save(new Staff("testuser", "test@example.com"));
	}

	@SuppressWarnings("unchecked")
	private void mockLlmResponse(String responseText) {
		WebClient.RequestBodyUriSpec requestBodyUriSpec = mock(WebClient.RequestBodyUriSpec.class);
		WebClient.RequestBodySpec requestBodySpec = mock(WebClient.RequestBodySpec.class);
		WebClient.ResponseSpec responseSpec = mock(WebClient.ResponseSpec.class);

		when(llmWebClient.post()).thenReturn(requestBodyUriSpec);
		when(requestBodyUriSpec.uri(any(String.class))).thenReturn(requestBodySpec);
		doReturn(requestBodySpec).when(requestBodySpec).bodyValue(any());
		doReturn(requestBodySpec).when(requestBodySpec).accept(any());
		when(requestBodySpec.retrieve()).thenReturn(responseSpec);

		com.sample.llm.dto.LlmResponse llmResponse = new com.sample.llm.dto.LlmResponse();
		llmResponse.setGeneratedText(responseText);

		when(responseSpec.bodyToMono(com.sample.llm.dto.LlmResponse.class))
				.thenReturn(Mono.just(llmResponse));
	}

	@Test
	@DisplayName("의료 상담 → DB 저장 → 히스토리 조회 통합 흐름")
	void medicalQuery_savesHistory_andRetrievable() throws Exception {
		mockLlmResponse("추천 진료과: 신경과\n두통 증상은 신경과 진료를 권장합니다.");

		// 1. 의료 상담 요청
		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-User-Id", testStaff.getId())
						.content("{\"query\": \"두통이 심합니다\"}"))
				.andExpect(status().isOk());

		// 2. DB에 이력이 저장되었는지 확인
		var histories = medicalHistoryRepository.findAll();
		assertThat(histories).hasSize(1);

		MedicalHistory saved = histories.get(0);
		assertThat(saved.getQuestion()).isEqualTo("두통이 심합니다");
		assertThat(saved.getStatus()).isEqualTo("COMPLETED");
		assertThat(saved.getAnswer()).contains("신경과");
		assertThat(saved.getStaff().getId()).isEqualTo(testStaff.getId());

		// 3. 히스토리 API로 조회
		mockMvc.perform(get("/api/medical/history/" + testStaff.getId()))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].question").value("두통이 심합니다"))
				.andExpect(jsonPath("$.content[0].status").value("COMPLETED"));
	}

	@Test
	@DisplayName("staffId 없이 의료 상담 → staff null로 저장")
	void medicalQuery_withoutStaffId_savesWithNullStaff() throws Exception {
		mockLlmResponse("일반 응답입니다.");

		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"일반 질문\"}"))
				.andExpect(status().isOk());

		var histories = medicalHistoryRepository.findAll();
		assertThat(histories).hasSize(1);
		assertThat(histories.get(0).getStaff()).isNull();
	}
}
