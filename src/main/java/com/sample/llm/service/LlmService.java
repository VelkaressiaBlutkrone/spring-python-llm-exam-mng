package com.sample.llm.service;

import com.sample.llm.dto.LlmResponse;
import com.sample.llm.entity.ChatbotHistory;
import com.sample.llm.entity.Staff;
import com.sample.llm.exception.LlmServiceUnavailableException;
import com.sample.llm.exception.LlmTimeoutException;
import com.sample.llm.repository.ChatbotHistoryRepository;
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
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeoutException;

@Service
@RequiredArgsConstructor
@Slf4j
public class LlmService {

	private final WebClient llmWebClient;
	private final ChatbotHistoryRepository chatbotHistoryRepository;
	private final StaffRepository staffRepository;
	private final ObjectMapper objectMapper;

	/**
	 * Python LLM 서버에 비동기 추론 요청을 보냅니다.
	 * RULE_SPRING.md: WebClient 비동기 호출 사용
	 */
	public Mono<String> callLlmApi(String query) {
		log.debug("LLM API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer/medical")
				.bodyValue(Map.of("query", query, "max_length", 512, "temperature", 0.3))
				.retrieve()
				.bodyToMono(LlmResponse.class)
				.map(LlmResponse::getGeneratedText)
				.onErrorMap(WebClientRequestException.class, e -> {
					if (e.getCause() instanceof ConnectTimeoutException) {
						return new LlmTimeoutException("LLM 서버 연결 타임아웃", e);
					}
					return new LlmServiceUnavailableException("LLM 서버 연결 실패", e);
				})
				.onErrorMap(TimeoutException.class, e ->
						new LlmTimeoutException("LLM 응답 시간 초과", e));
	}

	/**
	 * Python LLM 서버에 의학지식 기반 비동기 추론 요청을 보냅니다.
	 * /infer/medical 엔드포인트: MySQL 의학데이터 컨텍스트 주입 + Ollama 호출
	 */
	public Mono<String> callMedicalLlmApi(String query) {
		log.debug("Medical LLM API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer/medical")
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
						return new LlmTimeoutException("Medical LLM 서버 연결 타임아웃", e);
					}
					return new LlmServiceUnavailableException("Medical LLM 서버 연결 실패", e);
				})
				.onErrorMap(TimeoutException.class, e ->
						new LlmTimeoutException("Medical LLM 응답 시간 초과", e));
	}

	/**
	 * Python LLM 서버에 SSE 스트리밍 요청을 보냅니다.
	 * /infer/medical/stream → Ollama stream:true → 토큰 단위 SSE
	 */
	public Flux<String> callMedicalLlmApiStream(String query) {
		log.debug("Medical LLM Stream API 호출 시작 - query: {}", query);

		return llmWebClient.post()
				.uri("/infer/medical/stream")
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
						return new LlmTimeoutException("Medical LLM 서버 연결 타임아웃", e);
					}
					return new LlmServiceUnavailableException("Medical LLM 서버 연결 실패", e);
				})
				.onErrorMap(TimeoutException.class, e ->
						new LlmTimeoutException("Medical LLM 응답 시간 초과", e));
	}

	/**
	 * ChatbotHistory를 PENDING 상태로 저장합니다.
	 * staffId가 있으면 Staff를 조회하여 연결합니다. (ERD: CHATBOT_HISTORY.staff_id)
	 */
	@Transactional
	public ChatbotHistory savePending(String query, Long staffId) {
		ChatbotHistory history = new ChatbotHistory(query, "PENDING");

		if (staffId != null) {
			staffRepository.findById(staffId).ifPresent(history::setStaff);
		}

		ChatbotHistory saved = chatbotHistoryRepository.save(history);
		log.debug("ChatbotHistory PENDING 저장 - id: {}, staffId: {}", saved.getId(), staffId);
		return saved;
	}

	/**
	 * ChatbotHistory를 COMPLETED 상태로 업데이트합니다.
	 * metadata에 model, latency_ms 등 성능 정보를 저장합니다.
	 */
	@Transactional
	public void updateCompleted(Long historyId, String answer, long latencyMs) {
		chatbotHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setAnswer(answer);
			history.setStatus("COMPLETED");
			history.setMetadata(buildMetadata(latencyMs));
			chatbotHistoryRepository.save(history);
			log.debug("ChatbotHistory COMPLETED 업데이트 - id: {}, latency: {}ms", historyId, latencyMs);
		});
	}

	/**
	 * ChatbotHistory를 FAILED 상태로 업데이트합니다.
	 */
	@Transactional
	public void updateFailed(Long historyId, String errorMessage) {
		chatbotHistoryRepository.findById(historyId).ifPresent(history -> {
			history.setStatus("FAILED");
			history.setMetadata(buildErrorMetadata(errorMessage));
			chatbotHistoryRepository.save(history);
			log.warn("ChatbotHistory FAILED 업데이트 - id: {}, error: {}", historyId, errorMessage);
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
