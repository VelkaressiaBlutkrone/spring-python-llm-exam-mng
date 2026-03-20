package com.sample.llm.controller;

import com.sample.llm.dto.DoctorScheduleDto;
import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.entity.MedicalHistory;
import com.sample.llm.exception.LlmServiceUnavailableException;
import com.sample.llm.exception.LlmTimeoutException;
import com.sample.llm.repository.MedicalHistoryRepository;
import com.sample.llm.service.DoctorService;
import com.sample.llm.service.LlmResponseParser;
import com.sample.llm.service.MedicalService;
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
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MedicalController.class)
class MedicalControllerTest {

	@Autowired
	private MockMvc mockMvc;

	@MockitoBean
	private MedicalService medicalService;

	@MockitoBean
	private MedicalHistoryRepository medicalHistoryRepository;

	@MockitoBean
	private DoctorService doctorService;

	@MockitoBean
	private LlmResponseParser llmResponseParser;

	@Test
	@DisplayName("POST /api/medical/query - 정상 응답")
	void handleQuery_success() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("안녕하세요", "PENDING");
		pendingHistory.setId(1L);

		when(medicalService.saveMedicalPending(eq("안녕하세요"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callLlmApi("안녕하세요"))
				.thenReturn(Mono.just("Mock 응답"));

		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"안녕하세요\"}"))
				.andExpect(status().isOk())
				.andExpect(content().string("Mock 응답"));

		verify(medicalService).saveMedicalPending(eq("안녕하세요"), any());
		verify(medicalService).callLlmApi("안녕하세요");
	}

	@Test
	@DisplayName("POST /api/medical/query - X-User-Id 헤더 포함")
	void handleQuery_withUserId() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("테스트 쿼리", "PENDING");
		pendingHistory.setId(2L);

		when(medicalService.saveMedicalPending(eq("테스트 쿼리"), eq(42L)))
				.thenReturn(pendingHistory);
		when(medicalService.callLlmApi("테스트 쿼리"))
				.thenReturn(Mono.just("사용자 응답"));

		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-User-Id", "42")
						.content("{\"query\": \"테스트 쿼리\"}"))
				.andExpect(status().isOk())
				.andExpect(content().string("사용자 응답"));

		verify(medicalService).saveMedicalPending("테스트 쿼리", 42L);
	}

	@Test
	@DisplayName("POST /api/medical/query - LLM 서버 연결 실패 시 503")
	void handleQuery_serviceUnavailable() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("실패 쿼리", "PENDING");
		pendingHistory.setId(3L);

		when(medicalService.saveMedicalPending(eq("실패 쿼리"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callLlmApi("실패 쿼리"))
				.thenReturn(Mono.error(new LlmServiceUnavailableException(
						"LLM 서버 연결 실패", new RuntimeException("Connection refused"))));

		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"실패 쿼리\"}"))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.detail").value("LLM 서버를 사용할 수 없습니다"));
	}

	@Test
	@DisplayName("POST /api/medical/query - LLM 서버 타임아웃 시 504")
	void handleQuery_timeout() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("타임아웃 쿼리", "PENDING");
		pendingHistory.setId(4L);

		when(medicalService.saveMedicalPending(eq("타임아웃 쿼리"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callLlmApi("타임아웃 쿼리"))
				.thenReturn(Mono.error(new LlmTimeoutException(
						"LLM 응답 시간 초과", new RuntimeException("Timeout"))));

		mockMvc.perform(post("/api/medical/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"타임아웃 쿼리\"}"))
				.andExpect(status().isGatewayTimeout())
				.andExpect(jsonPath("$.detail").value("LLM 응답 시간 초과"));
	}

	@Test
	@DisplayName("POST /api/medical/medical-query - 정상 응답")
	void handleMedicalQuery_success() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("두통이 심한데 어느 과로 가야 하나요?", "PENDING");
		pendingHistory.setId(10L);

		when(medicalService.saveMedicalPending(eq("두통이 심한데 어느 과로 가야 하나요?"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callMedicalLlmApi("두통이 심한데 어느 과로 가야 하나요?"))
				.thenReturn(Mono.just("두통과 어지럼증 증상은 신경과 진료를 추천드립니다."));

		mockMvc.perform(post("/api/medical/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"두통이 심한데 어느 과로 가야 하나요?\"}"))
				.andExpect(status().isOk())
				.andExpect(content().string("두통과 어지럼증 증상은 신경과 진료를 추천드립니다."));

		verify(medicalService).saveMedicalPending(eq("두통이 심한데 어느 과로 가야 하나요?"), any());
		verify(medicalService).callMedicalLlmApi("두통이 심한데 어느 과로 가야 하나요?");
	}

	@Test
	@DisplayName("POST /api/medical/medical-query - LLM 서버 연결 실패 시 503")
	void handleMedicalQuery_serviceUnavailable() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("의학 질문", "PENDING");
		pendingHistory.setId(11L);

		when(medicalService.saveMedicalPending(eq("의학 질문"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callMedicalLlmApi("의학 질문"))
				.thenReturn(Mono.error(new LlmServiceUnavailableException(
						"Medical LLM 서버 연결 실패", new RuntimeException("Connection refused"))));

		mockMvc.perform(post("/api/medical/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"의학 질문\"}"))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.detail").value("LLM 서버를 사용할 수 없습니다"));
	}

	@Test
	@DisplayName("POST /api/medical/medical-query - LLM 타임아웃 시 504")
	void handleMedicalQuery_timeout() throws Exception {
		MedicalHistory pendingHistory = new MedicalHistory("타임아웃 의학 질문", "PENDING");
		pendingHistory.setId(12L);

		when(medicalService.saveMedicalPending(eq("타임아웃 의학 질문"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callMedicalLlmApi("타임아웃 의학 질문"))
				.thenReturn(Mono.error(new LlmTimeoutException(
						"Medical LLM 응답 시간 초과", new RuntimeException("Timeout"))));

		mockMvc.perform(post("/api/medical/medical-query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"타임아웃 의학 질문\"}"))
				.andExpect(status().isGatewayTimeout())
				.andExpect(jsonPath("$.detail").value("LLM 응답 시간 초과"));
	}

	@Test
	@DisplayName("GET /api/medical/history/{staffId} - 의학 히스토리 페이징 조회")
	void getHistory_success() throws Exception {
		MedicalHistory history1 = new MedicalHistory("첫 번째 질문", "COMPLETED");
		history1.setId(1L);
		history1.setSessionId("session-001");
		history1.setAnswer("첫 번째 응답");
		history1.setMetadata("{\"model\":\"gpt2\",\"latency_ms\":150}");
		history1.setCreatedAt(LocalDateTime.of(2025, 1, 15, 10, 30, 0));

		MedicalHistory history2 = new MedicalHistory("두 번째 질문", "COMPLETED");
		history2.setId(2L);
		history2.setSessionId("session-002");
		history2.setAnswer("두 번째 응답");
		history2.setMetadata("{\"model\":\"gpt2\",\"latency_ms\":200}");
		history2.setCreatedAt(LocalDateTime.of(2025, 1, 15, 11, 0, 0));

		Page<MedicalHistory> page = new PageImpl<>(
				List.of(history2, history1),
				PageRequest.of(0, 20),
				2
		);

		when(medicalHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(eq(1L), any()))
				.thenReturn(page);

		mockMvc.perform(get("/api/medical/history/1")
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
	@DisplayName("GET /api/medical/history/{staffId} - 빈 히스토리")
	void getHistory_empty() throws Exception {
		Page<MedicalHistory> emptyPage = new PageImpl<>(
				List.of(),
				PageRequest.of(0, 20),
				0
		);

		when(medicalHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(eq(999L), any()))
				.thenReturn(emptyPage);

		mockMvc.perform(get("/api/medical/history/999"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content").isArray())
				.andExpect(jsonPath("$.content.length()").value(0))
				.andExpect(jsonPath("$.totalElements").value(0));
	}

	@Test
	@DisplayName("POST /api/medical/query/consult - 진료과 + 의사 목록 통합 응답")
	void handleMedicalQueryWithDoctors_success() throws Exception {
		String llmResponse = "**추천 진료과**: 정형외과\n\n무릎 통증은 관절 문제를 의심할 수 있습니다.";

		MedicalHistory pendingHistory = new MedicalHistory("무릎이 아파요", "PENDING");
		pendingHistory.setId(20L);

		when(medicalService.saveMedicalPending(eq("무릎이 아파요"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callMedicalLlmApi("무릎이 아파요"))
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

		mockMvc.perform(post("/api/medical/query/consult")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"무릎이 아파요\"}"))
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
	@DisplayName("POST /api/medical/query/consult - 진료과 추출 실패 시 의사 목록 빈 배열")
	void handleMedicalQueryWithDoctors_noDepartment() throws Exception {
		String llmResponse = "일반적인 건강 상담 답변입니다.";

		MedicalHistory pendingHistory = new MedicalHistory("건강 상담", "PENDING");
		pendingHistory.setId(21L);

		when(medicalService.saveMedicalPending(eq("건강 상담"), any()))
				.thenReturn(pendingHistory);
		when(medicalService.callMedicalLlmApi("건강 상담"))
				.thenReturn(Mono.just(llmResponse));
		when(llmResponseParser.extractDepartment(llmResponse))
				.thenReturn(null);

		mockMvc.perform(post("/api/medical/query/consult")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"건강 상담\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.generatedText").value(llmResponse))
				.andExpect(jsonPath("$.recommendedDepartment").doesNotExist())
				.andExpect(jsonPath("$.doctors").isArray())
				.andExpect(jsonPath("$.doctors.length()").value(0));
	}
}
