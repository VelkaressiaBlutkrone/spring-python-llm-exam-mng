package com.sample.llm.controller;

import com.sample.llm.dto.ReservationRequest;
import com.sample.llm.dto.ReservationResponse;
import com.sample.llm.service.ReservationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RequiredArgsConstructor
@RestController
@RequestMapping("/api/reservation")
@Slf4j
public class ReservationApiController {

	private final ReservationService reservationService;

	@PostMapping
	public ResponseEntity<ReservationResponse.Max> createReservation(@RequestBody ReservationRequest.Save request) {
		ReservationResponse.Max result = reservationService.createReservation(request);
		log.info("예약 API 성공 - reservationId: {}", result.getId());
		return ResponseEntity.ok(result);
	}

	@GetMapping("/slots/{doctorId}")
	public ReservationResponse.SlotList getAvailableSlots(@PathVariable Long doctorId) {
		return reservationService.getAvailableSlots(doctorId);
	}
}
