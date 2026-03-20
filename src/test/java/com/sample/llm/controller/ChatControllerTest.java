package com.sample.llm.controller;

import com.sample.llm.dto.ChatHistoryResponse;
import com.sample.llm.service.ChatService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import reactor.core.publisher.Mono;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
class ChatControllerTest {

	@Autowired
	private MockMvc mockMvc;

	@MockitoBean
	private ChatService chatService;

	@Test
	@DisplayName("POST /api/chat/query - 병원 규칙 Q&A 정상 응답")
	void handleRuleQuery_success() throws Exception {
		when(chatService.callRuleLlmApi("당직 규칙이 뭔가요?"))
				.thenReturn(Mono.just("당직은 주 1회 교대 근무입니다."));

		mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.header("X-Staff-Id", "1")
						.content("{\"query\": \"당직 규칙이 뭔가요?\"}"))
				.andExpect(status().isOk())
				.andExpect(content().string("당직은 주 1회 교대 근무입니다."));
	}

	@Test
	@DisplayName("POST /api/chat/query - X-Staff-Id 누락 시 500 (GlobalExceptionHandler)")
	void handleRuleQuery_missingStaffId() throws Exception {
		mockMvc.perform(post("/api/chat/query")
						.contentType(MediaType.APPLICATION_JSON)
						.content("{\"query\": \"당직 규칙이 뭔가요?\"}"))
				.andExpect(status().isInternalServerError());
	}

	@Test
	@DisplayName("GET /api/chat/history/{staffId} - 규칙 Q&A 히스토리 조회")
	void getRuleHistory_success() throws Exception {
		ChatHistoryResponse r1 = new ChatHistoryResponse(1L, "session-1", "당직 규칙?", "주 1회 교대입니다.", null);
		ChatHistoryResponse r2 = new ChatHistoryResponse(2L, "session-1", "물품 요청 방법?", "물품 관리 시스템에서 신청하세요.", null);

		Page<ChatHistoryResponse> page = new PageImpl<>(
				List.of(r2, r1),
				PageRequest.of(0, 20),
				2
		);

		when(chatService.getChatHistory(eq(1L), any()))
				.thenReturn(page);

		mockMvc.perform(get("/api/chat/history/1")
						.param("page", "0")
						.param("size", "20"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content").isArray())
				.andExpect(jsonPath("$.content.length()").value(2))
				.andExpect(jsonPath("$.content[0].question").value("물품 요청 방법?"))
				.andExpect(jsonPath("$.content[1].question").value("당직 규칙?"))
				.andExpect(jsonPath("$.totalElements").value(2));
	}
}
