package com.sample.llm.controller;

import com.sample.llm.dto.ChatbotHistoryResponse;
import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.dto.LlmRequest;
import com.sample.llm.dto.MedicalLlmResponse;
import com.sample.llm.entity.ChatbotHistory;
import com.sample.llm.repository.ChatbotHistoryRepository;
import com.sample.llm.service.DoctorService;
import com.sample.llm.service.LlmResponseParser;
import com.sample.llm.service.LlmService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.MediaType;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/llm")
@RequiredArgsConstructor
@Slf4j
public class LlmController {

	private final LlmService llmService;
	private final ChatbotHistoryRepository chatbotHistoryRepository;
	private final DoctorService doctorService;
	private final LlmResponseParser llmResponseParser;

	/**
	 * POST /api/llm/query
	 * 비동기 파이프라인: PENDING 저장 → LLM 호출 → COMPLETED/FAILED 업데이트
	 *
	 * Step 7: userId 헤더 추출, metadata(latency_ms) 저장, 실패 사유 기록
	 */
	@PostMapping("/query")
	public Mono<String> handleQuery(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("LLM 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		// (DB 저장 1) PENDING 상태로 저장 (staffId가 있으면 Staff 연결, X-User-Id는 staffId로 사용)
		ChatbotHistory history = llmService.savePending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		// (API 호출) LLM 비동기 호출 → (DB 저장 2) 결과에 따라 상태 업데이트
		return llmService.callLlmApi(request.getQuery())
				.doOnNext(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					llmService.updateCompleted(history.getId(), response, latencyMs);
					log.info("LLM 응답 완료 - historyId: {}, latency: {}ms", history.getId(), latencyMs);
				})
				.doOnError(error -> {
					llmService.updateFailed(history.getId(), error.getMessage());
					log.error("LLM 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	/**
	 * POST /api/llm/medical-query
	 * 의학지식 데이터 기반 LLM 질의
	 * Python /infer/medical → MySQL 컨텍스트 조회 → Ollama 호출
	 */
	@PostMapping("/medical-query")
	public Mono<String> handleMedicalQuery(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical LLM 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		ChatbotHistory history = llmService.savePending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		return llmService.callMedicalLlmApi(request.getQuery())
				.doOnNext(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					llmService.updateCompleted(history.getId(), response, latencyMs);
					log.info("Medical LLM 응답 완료 - historyId: {}, latency: {}ms",
							history.getId(), latencyMs);
				})
				.doOnError(error -> {
					llmService.updateFailed(history.getId(), error.getMessage());
					log.error("Medical LLM 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	/**
	 * POST /api/llm/query/medical
	 * 의료 상담 + 추천 진료과 의사 목록 통합 반환
	 * Python /infer/medical 호출 → 진료과 파싱 → 의사 목록 조회 → 통합 응답
	 */
	@PostMapping("/query/medical")
	public Mono<MedicalLlmResponse> handleMedicalQueryWithDoctors(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical+Doctor 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		ChatbotHistory history = llmService.savePending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		return llmService.callMedicalLlmApi(request.getQuery())
				.map(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					llmService.updateCompleted(history.getId(), response, latencyMs);

					String department = llmResponseParser.extractDepartment(response);
					String reason = llmResponseParser.extractRecommendationReason(response);

					java.util.List<DoctorWithScheduleDto> doctors = (department != null)
							? doctorService.findDoctorsWithSchedule(department)
							: java.util.List.of();

					log.info("Medical+Doctor 응답 - dept: {}, doctors: {}, latency: {}ms",
							department, doctors.size(), latencyMs);

					return new MedicalLlmResponse(response, department, reason, doctors);
				})
				.doOnError(error -> {
					llmService.updateFailed(history.getId(), error.getMessage());
					log.error("Medical+Doctor 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	/**
	 * POST /api/llm/query/medical/stream
	 * SSE 스트리밍: 토큰 단위로 실시간 전송하여 체감 응답속도 개선
	 */
	@PostMapping(value = "/query/medical/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
	public Flux<String> handleMedicalQueryStream(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical Stream 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		return llmService.callMedicalLlmApiStream(request.getQuery());
	}

	/**
	 * GET /api/llm/history/{staffId}
	 * Step 9: 특정 사용자의 챗 히스토리를 페이징으로 조회합니다.
	 */
	@GetMapping("/history/{staffId}")
	public Page<ChatbotHistoryResponse> getHistory(
			@PathVariable Long staffId,
			@PageableDefault(size = 20) Pageable pageable) {

		log.debug("히스토리 조회 - staffId: {}, page: {}", staffId, pageable.getPageNumber());

		return chatbotHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
				.map(ChatbotHistoryResponse::from);
	}
}
