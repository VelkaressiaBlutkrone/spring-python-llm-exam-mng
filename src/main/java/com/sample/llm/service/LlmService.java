package com.sample.llm.service;

import com.sample.llm.dto.LlmResponse;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.repository.ChatHistoryRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class LlmService {

	private final WebClient llmWebClient;
	private final ChatHistoryRepository chatHistoryRepository;

	/**
	 * Python LLM 서버에 비동기 추론 요청을 보냅니다.
	 * RULE_SPRING.md: WebClient 비동기 호출 사용
	 */
	public Mono<String> callLlmApi(String query) {
		log.debug("LLM API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer")
				.bodyValue(Map.of("query", query))
				.retrieve()
				.bodyToMono(LlmResponse.class)
				.map(LlmResponse::getGeneratedText);
	}

	/**
	 * ChatHistory를 PENDING 상태로 저장합니다.
	 * RULE_SPRING.md: @Transactional 적용, status 필수 저장
	 */
	@Transactional
	public ChatHistory savePending(String query) {
		ChatHistory history = new ChatHistory(query, "PENDING");
		ChatHistory saved = chatHistoryRepository.save(history);
		log.debug("ChatHistory PENDING 저장 - id: {}", saved.getId());
		return saved;
	}

	/**
	 * ChatHistory를 COMPLETED 상태로 업데이트합니다.
	 */
	@Transactional
	public void updateCompleted(Long historyId, String response) {
		chatHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setResponse(response);
			history.setStatus("COMPLETED");
			chatHistoryRepository.save(history);
			log.debug("ChatHistory COMPLETED 업데이트 - id: {}", historyId);
		});
	}

	/**
	 * ChatHistory를 FAILED 상태로 업데이트합니다.
	 */
	@Transactional
	public void updateFailed(Long historyId) {
		chatHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setStatus("FAILED");
			chatHistoryRepository.save(history);
			log.warn("ChatHistory FAILED 업데이트 - id: {}", historyId);
		});
	}
}
