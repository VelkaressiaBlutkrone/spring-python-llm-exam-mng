package com.sample.llm.controller;

import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.dto.LlmRequest;
import com.sample.llm.dto.MedicalHistoryResponse;
import com.sample.llm.dto.MedicalLlmResponse;
import com.sample.llm.entity.MedicalHistory;
import com.sample.llm.repository.MedicalHistoryRepository;
import com.sample.llm.service.DoctorService;
import com.sample.llm.service.LlmResponseParser;
import com.sample.llm.service.MedicalService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RequiredArgsConstructor
@RestController
@RequestMapping("/api/medical")
@Slf4j
public class MedicalController {

	private final MedicalService medicalService;
	private final MedicalHistoryRepository medicalHistoryRepository;
	private final DoctorService doctorService;
	private final LlmResponseParser llmResponseParser;

	@PostMapping("/query")
	public Mono<String> handleQuery(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("LLM 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		MedicalHistory history = medicalService.saveMedicalPending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		return medicalService.callLlmApi(request.getQuery())
				.doOnNext(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
					log.info("LLM 응답 완료 - historyId: {}, latency: {}ms", history.getId(), latencyMs);
				})
				.doOnError(error -> {
					medicalService.updateMedicalFailed(history.getId(), error.getMessage());
					log.error("LLM 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	@PostMapping("/medical-query")
	public Mono<String> handleMedicalQuery(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical LLM 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		MedicalHistory history = medicalService.saveMedicalPending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		return medicalService.callMedicalLlmApi(request.getQuery())
				.doOnNext(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);
					log.info("Medical LLM 응답 완료 - historyId: {}, latency: {}ms",
							history.getId(), latencyMs);
				})
				.doOnError(error -> {
					medicalService.updateMedicalFailed(history.getId(), error.getMessage());
					log.error("Medical LLM 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	@PostMapping("/query/consult")
	public Mono<MedicalLlmResponse> handleMedicalQueryWithDoctors(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical+Doctor 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		MedicalHistory history = medicalService.saveMedicalPending(request.getQuery(), userId);
		long startTime = System.currentTimeMillis();

		return medicalService.callMedicalLlmApi(request.getQuery())
				.map(response -> {
					long latencyMs = System.currentTimeMillis() - startTime;
					medicalService.updateMedicalCompleted(history.getId(), response, latencyMs);

					String department = llmResponseParser.extractDepartment(response);
					String reason = llmResponseParser.extractRecommendationReason(response);

					java.util.List<DoctorWithScheduleDto> doctors = (department != null)
							? doctorService.findDoctorsWithSchedule(department)
							: java.util.List.of();

					log.info("Medical+Doctor 응답 - dept: {}, doctors: {}, latency: {}ms",
							department, doctors.size(), latencyMs);

					return new MedicalLlmResponse(response, department, reason, doctors);
				})
				.doOnError(error -> {
					medicalService.updateMedicalFailed(history.getId(), error.getMessage());
					log.error("Medical+Doctor 호출 실패 - historyId: {}, error: {}",
							history.getId(), error.getMessage());
				});
	}

	@PostMapping(value = "/query/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
	public Flux<String> handleMedicalQueryStream(
			@RequestBody LlmRequest request,
			@RequestHeader(value = "X-User-Id", required = false) Long userId) {

		log.debug("Medical Stream 쿼리 수신 - query: {}, userId: {}", request.getQuery(), userId);

		return medicalService.callMedicalLlmApiStream(request.getQuery());
	}

	@GetMapping("/history/{staffId}")
	public Page<MedicalHistoryResponse> getMedicalHistory(
			@PathVariable Long staffId,
			@PageableDefault(size = 20) Pageable pageable) {

		log.debug("의학 히스토리 조회 - staffId: {}, page: {}", staffId, pageable.getPageNumber());

		return medicalHistoryRepository.findByStaff_IdOrderByCreatedAtDesc(staffId, pageable)
				.map(MedicalHistoryResponse::from);
	}
}
