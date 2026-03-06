package com.sample.llm.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class LlmService {

	private final WebClient llmWebClient;

	public Mono<String> callLlmApi(String query) {
		log.debug("LLM API 호출: query={}", query != null && query.length() > 50 ? query.substring(0, 50) + "..." : query);

		return llmWebClient.post()
			.uri("/infer")
			.bodyValue(Map.of("query", query != null ? query : ""))
			.retrieve()
			.bodyToMono(InferResponse.class)
			.map(InferResponse::generatedText);
	}

	private record InferResponse(String generated_text) {
		public String generatedText() {
			return generated_text;
		}
	}
}
