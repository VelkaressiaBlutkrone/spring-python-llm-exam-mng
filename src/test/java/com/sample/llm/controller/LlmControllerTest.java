package com.sample.llm.controller;

import com.sample.llm.dto.DoctorScheduleDto;
import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.entity.ChatbotHistory;
import com.sample.llm.exception.LlmServiceUnavailableException;
import com.sample.llm.exception.LlmTimeoutException;
import com.sample.llm.repository.ChatbotHistoryRepository;
import com.sample.llm.service.DoctorService;
import com.sample.llm.service.LlmResponseParser;
import com.sample.llm.service.LlmService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.request;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * LlmController 단위 테스트
 * Step 10: @WebMvcTest + @MockitoBean 으로 실제 Python 서버 호출 없이 테스트
 */
@WebMvcTest(LlmController.class)
class LlmControllerTest {

	@Autowired
	private MockMvc mockMvc;

	@MockitoBean
	private LlmService llmService;

	@MockitoBean
	private ChatbotHistoryRepository chatbotHistoryRepository;

	@MockitoBean
	private DoctorService doctorService;

	@MockitoBean
	private LlmResponseParser llmResponseParser;

	// ============================================================
	// POST /api/llm/query 테스트
	// ============================================================

	@Test
	@DisplayName("POST /api/llm/query - 정상 응답")
	void handleQuery_success() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("안녕하세요", "PENDING");
		pendingHistory.setId(1L);

		when(llmService.savePending(eq("안녕하세요"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callLlmApi("안녕하세요"))
				.thenReturn(Mono.just("Mock 응답"));

		// when: Mono 반환은 비동기 처리 → asyncDispatch 필요
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"안녕하세요\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk())
				.andExpect(content().string("Mock 응답"));

		verify(llmService).savePending(eq("안녕하세요"), any());
		verify(llmService).callLlmApi("안녕하세요");
	}

	@Test
	@DisplayName("POST /api/llm/query - X-User-Id 헤더 포함")
	void handleQuery_withUserId() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("테스트 쿼리", "PENDING");
		pendingHistory.setId(2L);

		when(llmService.savePending(eq("테스트 쿼리"), eq(42L)))
				.thenReturn(pendingHistory);
		when(llmService.callLlmApi("테스트 쿼리"))
				.thenReturn(Mono.just("사용자 응답"));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-User-Id", "42")
						.content("{\"query\": \"테스트 쿼리\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk())
				.andExpect(content().string("사용자 응답"));

		verify(llmService).savePending("테스트 쿼리", 42L);
	}

	@Test
	@DisplayName("POST /api/llm/query - LLM 서버 연결 실패 시 503")
	void handleQuery_serviceUnavailable() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("실패 쿼리", "PENDING");
		pendingHistory.setId(3L);

		when(llmService.savePending(eq("실패 쿼리"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callLlmApi("실패 쿼리"))
				.thenReturn(Mono.error(new LlmServiceUnavailableException(
						"LLM 서버 연결 실패", new RuntimeException("Connection refused"))));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"실패 쿼리\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.detail").value("LLM 서버를 사용할 수 없습니다"));
	}

	@Test
	@DisplayName("POST /api/llm/query - LLM 서버 타임아웃 시 504")
	void handleQuery_timeout() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("타임아웃 쿼리", "PENDING");
		pendingHistory.setId(4L);

		when(llmService.savePending(eq("타임아웃 쿼리"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callLlmApi("타임아웃 쿼리"))
				.thenReturn(Mono.error(new LlmTimeoutException(
						"LLM 응답 시간 초과", new RuntimeException("Timeout"))));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"타임아웃 쿼리\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isGatewayTimeout())
				.andExpect(jsonPath("$.detail").value("LLM 응답 시간 초과"));
	}

	// ============================================================
	// POST /api/llm/medical-query 테스트
	// ============================================================

	@Test
	@DisplayName("POST /api/llm/medical-query - 정상 응답")
	void handleMedicalQuery_success() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("두통이 심한데 어느 과로 가야 하나요?", "PENDING");
		pendingHistory.setId(10L);

		when(llmService.savePending(eq("두통이 심한데 어느 과로 가야 하나요?"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callMedicalLlmApi("두통이 심한데 어느 과로 가야 하나요?"))
				.thenReturn(Mono.just("두통과 어지럼증 증상은 신경과 진료를 추천드립니다."));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"두통이 심한데 어느 과로 가야 하나요?\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk())
				.andExpect(content().string("두통과 어지럼증 증상은 신경과 진료를 추천드립니다."));

		verify(llmService).savePending(eq("두통이 심한데 어느 과로 가야 하나요?"), any());
		verify(llmService).callMedicalLlmApi("두통이 심한데 어느 과로 가야 하나요?");
	}

	@Test
	@DisplayName("POST /api/llm/medical-query - LLM 서버 연결 실패 시 503")
	void handleMedicalQuery_serviceUnavailable() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("의학 질문", "PENDING");
		pendingHistory.setId(11L);

		when(llmService.savePending(eq("의학 질문"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callMedicalLlmApi("의학 질문"))
				.thenReturn(Mono.error(new LlmServiceUnavailableException(
						"Medical LLM 서버 연결 실패", new RuntimeException("Connection refused"))));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"의학 질문\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.detail").value("LLM 서버를 사용할 수 없습니다"));
	}

	@Test
	@DisplayName("POST /api/llm/medical-query - LLM 타임아웃 시 504")
	void handleMedicalQuery_timeout() throws Exception {
		// given
		ChatbotHistory pendingHistory = new ChatbotHistory("타임아웃 의학 질문", "PENDING");
		pendingHistory.setId(12L);

		when(llmService.savePending(eq("타임아웃 의학 질문"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callMedicalLlmApi("타임아웃 의학 질문"))
				.thenReturn(Mono.error(new LlmTimeoutException(
						"Medical LLM 응답 시간 초과", new RuntimeException("Timeout"))));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"타임아웃 의학 질문\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isGatewayTimeout())
				.andExpect(jsonPath("$.detail").value("LLM 응답 시간 초과"));
	}

	// ============================================================
	// GET /api/llm/history/{userId} 테스트
	// ============================================================

	@Test
	@DisplayName("GET /api/llm/history/{userId} - 히스토리 페이징 조회")
	void getHistory_success() throws Exception {
		// given
		ChatbotHistory history1 = new ChatbotHistory("첫 번째 질문", "COMPLETED");
		history1.setId(1L);
		history1.setSessionId("session-001");
		history1.setAnswer("첫 번째 응답");
		history1.setMetadata("{\"model\":\"gpt2\",\"latency_ms\":150}");
		history1.setCreatedAt(LocalDateTime.of(2025, 1, 15, 10, 30, 0));

		ChatbotHistory history2 = new ChatbotHistory("두 번째 질문", "COMPLETED");
		history2.setId(2L);
		history2.setSessionId("session-002");
		history2.setAnswer("두 번째 응답");
		history2.setMetadata("{\"model\":\"gpt2\",\"latency_ms\":200}");
		history2.setCreatedAt(LocalDateTime.of(2025, 1, 15, 11, 0, 0));

		Page<ChatbotHistory> page = new PageImpl<>(
				List.of(history2, history1),
				PageRequest.of(0, 20),
				2
		);

		when(chatbotHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(eq(1L), any()))
				.thenReturn(page);

		// when & then (동기 응답 - asyncDispatch 불필요)
		mockMvc.perform(get("/api/llm/history/1")
						.param("page", "0")
						.param("size", "20"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content").isArray())
				.andExpect(jsonPath("$.content.length()").value(2))
				.andExpect(jsonPath("$.content[0].id").value(2))
				.andExpect(jsonPath("$.content[0].question").value("두 번째 질문"))
				.andExpect(jsonPath("$.content[0].answer").value("두 번째 응답"))
				.andExpect(jsonPath("$.content[0].status").value("COMPLETED"))
				.andExpect(jsonPath("$.totalElements").value(2))
				.andExpect(jsonPath("$.totalPages").value(1));
	}

	@Test
	@DisplayName("GET /api/llm/history/{userId} - 빈 히스토리")
	void getHistory_empty() throws Exception {
		// given
		Page<ChatbotHistory> emptyPage = new PageImpl<>(
				List.of(),
				PageRequest.of(0, 20),
				0
		);

		when(chatbotHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(eq(999L), any()))
				.thenReturn(emptyPage);

		// when & then
		mockMvc.perform(get("/api/llm/history/999"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content").isArray())
				.andExpect(jsonPath("$.content.length()").value(0))
				.andExpect(jsonPath("$.totalElements").value(0));
	}

	// ============================================================
	// POST /api/llm/query/medical 테스트
	// ============================================================

	@Test
	@DisplayName("POST /api/llm/query/medical - 진료과 + 의사 목록 통합 응답")
	void handleMedicalQueryWithDoctors_success() throws Exception {
		// given
		String llmResponse = "**추천 진료과**: 정형외과\n\n무릎 통증은 관절 문제를 의심할 수 있습니다.";

		ChatbotHistory pendingHistory = new ChatbotHistory("무릎이 아파요", "PENDING");
		pendingHistory.setId(20L);

		when(llmService.savePending(eq("무릎이 아파요"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callMedicalLlmApi("무릎이 아파요"))
				.thenReturn(Mono.just(llmResponse));
		when(llmResponseParser.extractDepartment(llmResponse))
				.thenReturn("정형외과");
		when(llmResponseParser.extractRecommendationReason(llmResponse))
				.thenReturn("무릎 통증은 관절 문제를 의심할 수 있습니다.");
		when(doctorService.findDoctorsWithSchedule("정형외과"))
				.thenReturn(List.of(
						new DoctorWithScheduleDto(1L, "김정형", "정형외과", "관절외과", "서울대학교병원", null, null, null,
								List.of(new DoctorScheduleDto("MON", LocalTime.of(9, 0), LocalTime.of(17, 0), true))),
						new DoctorWithScheduleDto(2L, "이관절", "정형외과", "척추외과", "세브란스병원", null, null, null,
								List.of(new DoctorScheduleDto("TUE", LocalTime.of(10, 0), LocalTime.of(18, 0), true)))
				));

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query/medical")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"무릎이 아파요\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.generatedText").value(llmResponse))
				.andExpect(jsonPath("$.recommendedDepartment").value("정형외과"))
				.andExpect(jsonPath("$.recommendationReason").value("무릎 통증은 관절 문제를 의심할 수 있습니다."))
				.andExpect(jsonPath("$.doctors").isArray())
				.andExpect(jsonPath("$.doctors.length()").value(2))
				.andExpect(jsonPath("$.doctors[0].name").value("김정형"))
				.andExpect(jsonPath("$.doctors[1].name").value("이관절"));
	}

	@Test
	@DisplayName("POST /api/llm/query/medical - 진료과 추출 실패 시 의사 목록 빈 배열")
	void handleMedicalQueryWithDoctors_noDepartment() throws Exception {
		// given
		String llmResponse = "일반적인 건강 상담 답변입니다.";

		ChatbotHistory pendingHistory = new ChatbotHistory("건강 상담", "PENDING");
		pendingHistory.setId(21L);

		when(llmService.savePending(eq("건강 상담"), any()))
				.thenReturn(pendingHistory);
		when(llmService.callMedicalLlmApi("건강 상담"))
				.thenReturn(Mono.just(llmResponse));
		when(llmResponseParser.extractDepartment(llmResponse))
				.thenReturn(null);

		// when
		MvcResult mvcResult = mockMvc.perform(post("/api/llm/query/medical")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"건강 상담\"}"))
				.andExpect(request().asyncStarted())
				.andReturn();

		// then
		mockMvc.perform(asyncDispatch(mvcResult))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.generatedText").value(llmResponse))
				.andExpect(jsonPath("$.recommendedDepartment").doesNotExist())
				.andExpect(jsonPath("$.doctors").isArray())
				.andExpect(jsonPath("$.doctors.length()").value(0));
	}
}
