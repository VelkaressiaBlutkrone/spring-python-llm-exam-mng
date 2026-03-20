package com.sample.llm.service;

import com.sample.llm.dto.LlmResponse;
import com.sample.llm.dto.MedicalHistoryResponse;
import com.sample.llm.entity.MedicalHistory;
import com.sample.llm.exception.LlmServiceUnavailableException;
import com.sample.llm.exception.LlmTimeoutException;
import com.sample.llm.repository.MedicalHistoryRepository;
import com.sample.llm.repository.StaffRepository;
import io.netty.channel.ConnectTimeoutException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeoutException;

@Transactional(readOnly = true)
@RequiredArgsConstructor
@Service
@Slf4j
public class MedicalService {

	private final WebClient llmWebClient;
	private final MedicalHistoryRepository medicalHistoryRepository;
	private final StaffRepository staffRepository;
	private final ObjectMapper objectMapper;

	public Mono<String> callLlmApi(String query) {
		log.debug("LLM API 호출 시작 - query: {}", query);
		return callMedicalLlmApi(query);
	}

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

	@Transactional
	public MedicalHistory saveMedicalPending(String query, Long staffId) {
		MedicalHistory history = new MedicalHistory(query, "PENDING");

		if (staffId != null) {
			staffRepository.findById(staffId).ifPresent(history::setStaff);
		}

		MedicalHistory saved = medicalHistoryRepository.save(history);
		log.debug("MedicalHistory PENDING 저장 - id: {}, staffId: {}", saved.getId(), staffId);
		return saved;
	}

	@Transactional
	public void updateMedicalCompleted(Long historyId, String answer, long latencyMs) {
		MedicalHistory history = medicalHistoryRepository.findById(historyId)
				.orElseThrow(() -> new IllegalStateException("MedicalHistory not found: " + historyId));
		history.setAnswer(answer);
		history.setStatus("COMPLETED");
		history.setMetadata(buildMetadata(latencyMs));
		medicalHistoryRepository.save(history);
		log.debug("MedicalHistory COMPLETED 업데이트 - id: {}, latency: {}ms", historyId, latencyMs);
	}

	@Transactional
	public void updateMedicalFailed(Long historyId, String errorMessage) {
		MedicalHistory history = medicalHistoryRepository.findById(historyId)
				.orElseThrow(() -> new IllegalStateException("MedicalHistory not found: " + historyId));
		history.setStatus("FAILED");
		history.setMetadata(buildErrorMetadata(errorMessage));
		medicalHistoryRepository.save(history);
		log.warn("MedicalHistory FAILED 업데이트 - id: {}, error: {}", historyId, errorMessage);
	}

	private String buildMetadata(long latencyMs) {
		Map<String, Object> meta = new LinkedHashMap<>();
		meta.put("model", "qwen2.5:7b");
		meta.put("latency_ms", latencyMs);
		return toJson(meta);
	}

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

	public Page<MedicalHistoryResponse> getMedicalHistory(Long staffId, Pageable pageable) {
		return medicalHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
				.map(MedicalHistoryResponse::from);
	}
}
