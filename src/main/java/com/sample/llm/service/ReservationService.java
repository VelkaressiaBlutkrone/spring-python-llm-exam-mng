package com.sample.llm.service;

import com.sample.llm.dto.ReservationRequest;
import com.sample.llm.dto.ReservationResponse;
import com.sample.llm.entity.Doctor;
import com.sample.llm.entity.Reservation;
import com.sample.llm.repository.DoctorRepository;
import com.sample.llm.repository.DoctorScheduleRepository;
import com.sample.llm.repository.ReservationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Transactional(readOnly = true)
@RequiredArgsConstructor
@Service
@Slf4j
public class ReservationService {

	private final ReservationRepository reservationRepository;
	private final DoctorRepository doctorRepository;
	private final DoctorScheduleRepository doctorScheduleRepository;

	@Transactional
	public ReservationResponse.Max createReservation(ReservationRequest.Save request) {
		Doctor doctor = doctorRepository.findById(request.getDoctorId())
				.orElseThrow(() -> new IllegalArgumentException("Doctor not found: " + request.getDoctorId()));

		long existing = reservationRepository.countByDoctorIdAndReservationDateAndStartTime(
				request.getDoctorId(), request.getReservationDate(), request.getStartTime());
		if (existing > 0) {
			throw new IllegalStateException("해당 시간대에 이미 예약이 존재합니다.");
		}

		Reservation reservation = new Reservation(
				doctor, null,
				request.getReservationDate(),
				request.getStartTime(),
				request.getEndTime(),
				"CONFIRMED"
		);

		Reservation saved = reservationRepository.save(reservation);
		log.info("예약 생성 완료 - id: {}, doctorId: {}, date: {}", saved.getId(), doctor.getId(), request.getReservationDate());
		return ReservationResponse.Max.from(saved);
	}

	public ReservationResponse.SlotList getAvailableSlots(Long doctorId) {
		Doctor doctor = doctorRepository.findById(doctorId)
				.orElseThrow(() -> new IllegalArgumentException("Doctor not found: " + doctorId));

		var schedules = doctorScheduleRepository.findByDoctorIdAndIsAvailableTrue(doctorId);

		LocalDate today = LocalDate.now();
		LocalDate startDate = today.plusDays(1);
		LocalDate endDate = today.plusDays(8);

		// 해당 기간 예약을 한 번에 조회
		List<Reservation> existingReservations = reservationRepository
				.findByDoctorIdAndReservationDateBetween(doctorId, startDate, endDate);

		Set<String> reservedKeys = existingReservations.stream()
				.map(r -> r.getReservationDate() + "_" + r.getStartTime())
				.collect(Collectors.toSet());

		List<ReservationResponse.Slot> slots = new ArrayList<>();

		for (int dayOffset = 1; dayOffset <= 7; dayOffset++) {
			LocalDate date = today.plusDays(dayOffset);
			DayOfWeek dow = date.getDayOfWeek();
			String dayCode = toEnglishDayCode(dow);

			schedules.stream()
					.filter(s -> s.getDayOfWeek().equalsIgnoreCase(dayCode))
					.forEach(schedule -> {
						LocalTime slotTime = schedule.getStartTime();
						while (slotTime.isBefore(schedule.getEndTime())) {
							LocalTime slotEnd = slotTime.plusMinutes(30);
							if (slotEnd.isAfter(schedule.getEndTime())) break;

							boolean available = !reservedKeys.contains(date + "_" + slotTime);
							slots.add(new ReservationResponse.Slot(date, slotTime, slotEnd, available));
							slotTime = slotEnd;
						}
					});

			if (slots.size() >= 12) break;
		}

		return new ReservationResponse.SlotList(doctorId, doctor.getName(), slots);
	}

	private String toEnglishDayCode(DayOfWeek dow) {
		return switch (dow) {
			case MONDAY -> "MON";
			case TUESDAY -> "TUE";
			case WEDNESDAY -> "WED";
			case THURSDAY -> "THU";
			case FRIDAY -> "FRI";
			case SATURDAY -> "SAT";
			case SUNDAY -> "SUN";
		};
	}
}
