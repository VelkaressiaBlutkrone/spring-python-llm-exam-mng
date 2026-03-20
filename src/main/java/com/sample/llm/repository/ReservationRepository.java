package com.sample.llm.repository;

import com.sample.llm.entity.Reservation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

public interface ReservationRepository extends JpaRepository<Reservation, Integer> {

	List<Reservation> findByDoctorIdAndReservationDate(Long doctorId, LocalDate reservationDate);

	long countByDoctorIdAndReservationDateAndStartTime(Long doctorId, LocalDate reservationDate, LocalTime startTime);

	List<Reservation> findByDoctorIdAndReservationDateBetween(Long doctorId, LocalDate startDate, LocalDate endDate);
}
