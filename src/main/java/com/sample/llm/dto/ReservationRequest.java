package com.sample.llm.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalTime;

public class ReservationRequest {

	@Data
	public static class Save {
		private Long doctorId;
		private LocalDate reservationDate;
		private LocalTime startTime;
		private LocalTime endTime;
	}
}
