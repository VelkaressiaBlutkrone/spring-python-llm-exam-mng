package com.sample.llm.exception;

/**
 * Python LLM 서버 응답 타임아웃 시 발생하는 예외 (504)
 */
public class LlmTimeoutException extends RuntimeException {

	public LlmTimeoutException(String message, Throwable cause) {
		super(message, cause);
	}
}
