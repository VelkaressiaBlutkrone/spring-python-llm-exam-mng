package com.sample.llm.service;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;
import com.sample.llm.dto.LlmResponse;
import com.sample.llm.entity.ChatHistory;
import com.sample.llm.entity.User;
import com.sample.llm.repository.ChatHistoryRepository;
import com.sample.llm.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.LinkedHashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class LlmService {

	private final WebClient llmWebClient;
	private final ChatHistoryRepository chatHistoryRepository;
	private final UserRepository userRepository;
	private final ObjectMapper objectMapper;

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
	 * Step 7: userId가 있으면 User를 조회하여 연결합니다.
	 * RULE_SPRING.md: @Transactional 적용, status 필수 저장
	 */
	@Transactional
	public ChatHistory savePending(String query, Long userId) {
		ChatHistory history = new ChatHistory(query, "PENDING");

		if (userId != null) {
			userRepository.findById(userId).ifPresent(history::setUser);
		}

		ChatHistory saved = chatHistoryRepository.save(history);
		log.debug("ChatHistory PENDING 저장 - id: {}, userId: {}", saved.getId(), userId);
		return saved;
	}

	/**
	 * ChatHistory를 COMPLETED 상태로 업데이트합니다.
	 * Step 7: metadata에 model, latency_ms 등 성능 정보를 저장합니다.
	 */
	@Transactional
	public void updateCompleted(Long historyId, String response, long latencyMs) {
		chatHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setResponse(response);
			history.setStatus("COMPLETED");
			history.setMetadata(buildMetadata(latencyMs));
			chatHistoryRepository.save(history);
			log.debug("ChatHistory COMPLETED 업데이트 - id: {}, latency: {}ms", historyId, latencyMs);
		});
	}

	/**
	 * ChatHistory를 FAILED 상태로 업데이트합니다.
	 * Step 7: doOnError에서 호출되어 실패 사유를 기록합니다.
	 */
	@Transactional
	public void updateFailed(Long historyId, String errorMessage) {
		chatHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setStatus("FAILED");
			history.setMetadata(buildErrorMetadata(errorMessage));
			chatHistoryRepository.save(history);
			log.warn("ChatHistory FAILED 업데이트 - id: {}, error: {}", historyId, errorMessage);
		});
	}

	/**
	 * 성공 시 metadata JSON 생성 (model, latency_ms)
	 */
	private String buildMetadata(long latencyMs) {
		Map<String, Object> meta = new LinkedHashMap<>();
		meta.put("model", "gpt2");
		meta.put("latency_ms", latencyMs);
		return toJson(meta);
	}

	/**
	 * 실패 시 metadata JSON 생성 (error)
	 */
	private String buildErrorMetadata(String errorMessage) {
		Map<String, Object> meta = new LinkedHashMap<>();
		meta.put("error", errorMessage);
		return toJson(meta);
	}

	private String toJson(Map<String, Object> map) {
		try {
			return objectMapper.writeValueAsString(map);
		} catch (JacksonException e) {
			log.error("metadata JSON 변환 실패", e);
			return "{}";
		}
	}
}
