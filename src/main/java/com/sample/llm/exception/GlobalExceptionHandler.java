package com.sample.llm.exception;

import com.sample.llm.dto.ErrorResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.reactive.function.client.WebClientResponseException;

/**
 * 전역 예외 처리 - RULE_SPRING.md Section 4
 * Python 서버 장애 시 적절한 HTTP 상태와 메시지를 반환합니다.
 */
@ControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

	/**
	 * Python LLM 서버 연결 실패 → 503 Service Unavailable
	 */
	@ExceptionHandler(LlmServiceUnavailableException.class)
	public ResponseEntity<ErrorResponse> handleLlmServiceUnavailable(LlmServiceUnavailableException e) {
		log.error("LLM 서버 사용 불가: {}", e.getMessage());
		return ResponseEntity
				.status(HttpStatus.SERVICE_UNAVAILABLE)
				.body(new ErrorResponse("LLM 서버를 사용할 수 없습니다"));
	}

	/**
	 * Python LLM 서버 응답 타임아웃 → 504 Gateway Timeout
	 */
	@ExceptionHandler(LlmTimeoutException.class)
	public ResponseEntity<ErrorResponse> handleLlmTimeout(LlmTimeoutException e) {
		log.error("LLM 응답 시간 초과: {}", e.getMessage());
		return ResponseEntity
				.status(HttpStatus.GATEWAY_TIMEOUT)
				.body(new ErrorResponse("LLM 응답 시간 초과"));
	}

	/**
	 * Python 서버 5xx 에러 → 503 Service Unavailable
	 */
	@ExceptionHandler(WebClientResponseException.class)
	public ResponseEntity<ErrorResponse> handleWebClientResponseException(WebClientResponseException e) {
		log.error("Python 서버 에러 - status: {}, body: {}", e.getStatusCode(), e.getResponseBodyAsString());
		return ResponseEntity
				.status(HttpStatus.SERVICE_UNAVAILABLE)
				.body(new ErrorResponse("LLM 서버 오류: " + e.getStatusCode()));
	}

	/**
	 * 비즈니스 로직 검증 실패 → 400 Bad Request
	 */
	@ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
	public ResponseEntity<ErrorResponse> handleBusinessException(RuntimeException e) {
		log.warn("비즈니스 예외: {}", e.getMessage());
		return ResponseEntity
				.badRequest()
				.body(new ErrorResponse(e.getMessage()));
	}

	/**
	 * Bean Validation 실패 → 400 Bad Request
	 */
	@ExceptionHandler(org.springframework.web.bind.MethodArgumentNotValidException.class)
	public ResponseEntity<ErrorResponse> handleValidationException(
			org.springframework.web.bind.MethodArgumentNotValidException e) {
		String message = e.getBindingResult().getFieldErrors().stream()
				.map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
				.findFirst()
				.orElse("입력값 검증 실패");
		log.warn("Validation 예외: {}", message);
		return ResponseEntity
				.badRequest()
				.body(new ErrorResponse(message));
	}

	/**
	 * 기타 예상치 못한 예외 → 500 Internal Server Error
	 */
	@ExceptionHandler(Exception.class)
	public ResponseEntity<ErrorResponse> handleGenericException(Exception e) {
		log.error("서버 내부 오류: {}", e.getMessage(), e);
		return ResponseEntity
				.status(HttpStatus.INTERNAL_SERVER_ERROR)
				.body(new ErrorResponse("서버 내부 오류가 발생했습니다"));
	}
}
