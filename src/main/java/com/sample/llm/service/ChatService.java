package com.sample.llm.service;

import com.sample.llm.dto.LlmResponse;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.entity.Staff;
import com.sample.llm.exception.LlmServiceUnavailableException;
import com.sample.llm.exception.LlmTimeoutException;
import com.sample.llm.repository.ChatHistoryRepository;
import com.sample.llm.repository.StaffRepository;
import io.netty.channel.ConnectTimeoutException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.http.MediaType;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.concurrent.TimeoutException;

@Transactional(readOnly = true)
@RequiredArgsConstructor
@Service
@Slf4j
public class ChatService {

	private final WebClient llmWebClient;
	private final ChatHistoryRepository chatHistoryRepository;
	private final StaffRepository staffRepository;

	public Mono<String> callRuleLlmApi(String query) {
		log.debug("Rule LLM API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer/rule")
				.bodyValue(Map.of(
						"query", query,
						"max_length", 512,
						"temperature", 0.3
				))
				.retrieve()
				.bodyToMono(LlmResponse.class)
				.map(LlmResponse::getGeneratedText)
				.onErrorMap(WebClientRequestException.class, e -> {
					if (e.getCause() instanceof ConnectTimeoutException) {
						return new LlmTimeoutException("Rule LLM 서버 연결 타임아웃", e);
					}
					return new LlmServiceUnavailableException("Rule LLM 서버 연결 실패", e);
				})
				.onErrorMap(TimeoutException.class, e ->
						new LlmTimeoutException("Rule LLM 응답 시간 초과", e));
	}

	public Flux<String> callRuleLlmApiStream(String query) {
		log.debug("Rule LLM Stream API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer/rule/stream")
				.bodyValue(Map.of(
						"query", query,
						"max_length", 512,
						"temperature", 0.3
				))
				.accept(MediaType.TEXT_EVENT_STREAM)
				.retrieve()
				.bodyToFlux(String.class)
				.onErrorMap(WebClientRequestException.class, e -> {
					if (e.getCause() instanceof ConnectTimeoutException) {
						return new LlmTimeoutException("Rule LLM 서버 연결 타임아웃", e);
					}
					return new LlmServiceUnavailableException("Rule LLM 서버 연결 실패", e);
				})
				.onErrorMap(TimeoutException.class, e ->
						new LlmTimeoutException("Rule LLM 응답 시간 초과", e));
	}

	@Transactional
	public ChatHistory saveChatHistory(Long staffId, String sessionId, String question, String answer) {
		Staff staff = staffRepository.findById(staffId)
				.orElseThrow(() -> new IllegalArgumentException("Staff not found: " + staffId));

		ChatHistory history = new ChatHistory(staff, sessionId, question, answer);
		ChatHistory saved = chatHistoryRepository.save(history);
		log.debug("ChatHistory 저장 - id: {}, staffId: {}", saved.getId(), staffId);
		return saved;
	}
}
