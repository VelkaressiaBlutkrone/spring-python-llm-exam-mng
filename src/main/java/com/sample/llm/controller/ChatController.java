package com.sample.llm.controller;

import com.sample.llm.dto.ChatHistoryResponse;
import com.sample.llm.dto.LlmRequest;
import com.sample.llm.repository.ChatHistoryRepository;
import com.sample.llm.service.ChatService;
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

@RequiredArgsConstructor
@RestController
@RequestMapping("/api/chat")
@Slf4j
public class ChatController {

	private final ChatService chatService;
	private final ChatHistoryRepository chatHistoryRepository;

	@PostMapping("/query")
	public Mono<String> handleRuleQuery(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-Staff-Id", required = true) Long staffId,
			@RequestHeader(value = "X-Session-Id", required = false) String sessionId) {

		log.debug("Rule Q&A 쿼리 수신 - query: {}, staffId: {}", request.getQuery(), staffId);

		String effectiveSessionId = sessionId != null ? sessionId : "session-" + staffId + "-" + System.currentTimeMillis();

		return chatService.callRuleLlmApi(request.getQuery())
				.doOnNext(answer -> {
					try {
						chatService.saveChatHistory(staffId, effectiveSessionId, request.getQuery(), answer);
						log.info("Rule Q&A 저장 완료 - staffId: {}", staffId);
					} catch (Exception e) {
						log.error("Rule Q&A 히스토리 저장 실패 - staffId: {}, error: {}", staffId, e.getMessage(), e);
					}
				});
	}

	@GetMapping("/history/{staffId}")
	public Page<ChatHistoryResponse> getRuleHistory(
			@PathVariable Long staffId,
			@PageableDefault(size = 20) Pageable pageable) {

		log.debug("규칙 Q&A 히스토리 조회 - staffId: {}, page: {}", staffId, pageable.getPageNumber());

		return chatHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
				.map(ChatHistoryResponse::from);
	}
}
