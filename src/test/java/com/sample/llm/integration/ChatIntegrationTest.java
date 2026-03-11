package com.sample.llm.integration;

import com.sample.llm.entity.ChatHistory;
import com.sample.llm.entity.Staff;
import com.sample.llm.repository.ChatHistoryRepository;
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
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class ChatIntegrationTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private StaffRepository staffRepository;

	@Autowired
	private ChatHistoryRepository chatHistoryRepository;

	@Autowired
	private com.sample.llm.repository.MedicalHistoryRepository medicalHistoryRepository;

	@MockitoBean
	private WebClient llmWebClient;

	private Staff testStaff;

	@BeforeEach
	void setUp() {
		chatHistoryRepository.deleteAll();
		medicalHistoryRepository.deleteAll();
		staffRepository.deleteAll();
		testStaff = staffRepository.save(new Staff("nurse1", "nurse1@hospital.com"));
	}

	@SuppressWarnings("unchecked")
	private void mockRuleLlmResponse(String responseText) {
		WebClient.RequestBodyUriSpec requestBodyUriSpec = mock(WebClient.RequestBodyUriSpec.class);
		WebClient.RequestBodySpec requestBodySpec = mock(WebClient.RequestBodySpec.class);
		WebClient.ResponseSpec responseSpec = mock(WebClient.ResponseSpec.class);

		when(llmWebClient.post()).thenReturn(requestBodyUriSpec);
		when(requestBodyUriSpec.uri(any(String.class))).thenReturn(requestBodySpec);
		doReturn(requestBodySpec).when(requestBodySpec).bodyValue(any());
		when(requestBodySpec.retrieve()).thenReturn(responseSpec);

		com.sample.llm.dto.LlmResponse llmResponse = new com.sample.llm.dto.LlmResponse();
		llmResponse.setGeneratedText(responseText);

		when(responseSpec.bodyToMono(com.sample.llm.dto.LlmResponse.class))
				.thenReturn(Mono.just(llmResponse));
	}

	@Test
	@DisplayName("병원 규칙 Q&A → chatbot_history 저장 → 히스토리 조회 통합 흐름")
	void ruleQuery_savesHistory_andRetrievable() throws Exception {
		mockRuleLlmResponse("당직은 주 1회 교대 근무이며, 야간 당직은 오후 6시부터 다음 날 오전 9시까지입니다.");

		// 1. 규칙 Q&A 요청
		MvcResult mvcResult = mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-Staff-Id", testStaff.getId())
						.content("{\"query\": \"당직 근무 규정이 어떻게 되나요?\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk());

		// 2. chatbot_history 테이블에 저장 확인
		var histories = chatHistoryRepository.findAll();
		assertThat(histories).hasSize(1);

		ChatHistory saved = histories.get(0);
		assertThat(saved.getQuestion()).isEqualTo("당직 근무 규정이 어떻게 되나요?");
		assertThat(saved.getAnswer()).contains("당직");
		assertThat(saved.getStaff().getId()).isEqualTo(testStaff.getId());
		assertThat(saved.getSessionId()).startsWith("session-");

		// 3. 히스토리 API로 조회
		mockMvc.perform(get("/api/chat/history/" + testStaff.getId()))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].question").value("당직 근무 규정이 어떻게 되나요?"))
				.andExpect(jsonPath("$.content[0].answer").exists());
	}

	@Test
	@DisplayName("X-Staff-Id 누락 시 에러 반환")
	void ruleQuery_missingStaffId_returns500() throws Exception {
		mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"당직 규칙?\"}"))
				.andExpect(status().isInternalServerError());
	}

	@Test
	@DisplayName("여러 질문 후 히스토리에 순서대로 저장")
	void multipleQueries_savedInOrder() throws Exception {
		mockRuleLlmResponse("첫 번째 답변");

		MvcResult r1 = mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-Staff-Id", testStaff.getId())
						.content("{\"query\": \"질문 1\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();
		mockMvc.perform(asyncDispatch(r1)).andExpect(status().isOk());

		mockRuleLlmResponse("두 번째 답변");

		MvcResult r2 = mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-Staff-Id", testStaff.getId())
						.content("{\"query\": \"질문 2\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();
		mockMvc.perform(asyncDispatch(r2)).andExpect(status().isOk());

		var histories = chatHistoryRepository.findAll();
		assertThat(histories).hasSize(2);

		mockMvc.perform(get("/api/chat/history/" + testStaff.getId()))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(2))
				.andExpect(jsonPath("$.totalElements").value(2));
	}
}
