package com.sample.llm.controller;

import com.sample.llm.dto.LlmRequest;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.service.LlmService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
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
	 * TASK_SPRING.md Step 6:
	 *   (DB 저장 1) ChatHistory PENDING 저장
	 *   (API 호출)  llmService.callLlmApi() Mono 스트림
	 *   (DB 저장 2) doOnNext로 COMPLETED 업데이트, doOnError로 FAILED 업데이트
	 */
	@PostMapping("/query")
	public Mono<String> handleQuery(@RequestBody LlmRequest request) {
		log.debug("LLM 쿼리 수신 - query: {}", request.getQuery());

		// (DB 저장 1) PENDING 상태로 저장
		ChatHistory history = llmService.savePending(request.getQuery());

		// (API 호출) LLM 비동기 호출 → (DB 저장 2) 결과에 따라 상태 업데이트
		return llmService.callLlmApi(request.getQuery())
				.doOnNext(response -> {
					llmService.updateCompleted(history.getId(), response);
					log.info("LLM 응답 완료 - historyId: {}", history.getId());
				})
				.doOnError(error -> {
					llmService.updateFailed(history.getId());
					log.error("LLM 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}
}
