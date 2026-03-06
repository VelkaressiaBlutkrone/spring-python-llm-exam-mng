package com.sample.llm.controller;

import com.sample.llm.dto.LlmRequest;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.service.LlmService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
}
