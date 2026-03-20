package com.sample.llm.exception;

/**
 * Python LLM 서버 연결 실패 시 발생하는 예외 (503)
 */
public class LlmServiceUnavailableException extends RuntimeException {

	public LlmServiceUnavailableException(String message, Throwable cause) {
		super(message, cause);
	}
}
