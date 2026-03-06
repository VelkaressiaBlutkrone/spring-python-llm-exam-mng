package com.sample.llm.controller;

import com.sample.llm.dto.ChatHistoryResponse;
import com.sample.llm.dto.LlmRequest;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.repository.ChatHistoryRepository;
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
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/llm")
@RequiredArgsConstructor
@Slf4j
public class LlmController {

	private final LlmService llmService;
	private final ChatHistoryRepository chatHistoryRepository;

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

		// (DB 저장 1) PENDING 상태로 저장 (userId가 있으면 User 연결)
		ChatHistory history = llmService.savePending(request.getQuery(), userId);
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

		ChatHistory history = llmService.savePending(request.getQuery(), userId);
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
	 * GET /api/llm/history/{userId}
	 * Step 9: 특정 사용자의 챗 히스토리를 페이징으로 조회합니다.
	 */
	@GetMapping("/history/{userId}")
	public Page<ChatHistoryResponse> getHistory(
			@PathVariable Long userId,
			@PageableDefault(size = 20) Pageable pageable) {

		log.debug("히스토리 조회 - userId: {}, page: {}", userId, pageable.getPageNumber());

		return chatHistoryRepository.findByUser_IdOrderByTimestampDesc(userId, pageable)
				.map(ChatHistoryResponse::from);
	}
}
