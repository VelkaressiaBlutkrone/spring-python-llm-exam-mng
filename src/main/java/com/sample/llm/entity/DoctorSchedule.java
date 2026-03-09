package com.sample.llm.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalTime;

@Entity
@Table(name = "doctor_schedule")
@Getter
@Setter
@NoArgsConstructor
public class DoctorSchedule {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@ManyToOne
	@JoinColumn(name = "doctor_id", nullable = false)
	private Doctor doctor;

	@Column(name = "day_of_week", nullable = false, length = 10)
	private String dayOfWeek;

	@Column(name = "start_time", nullable = false)
	private LocalTime startTime;

	@Column(name = "end_time", nullable = false)
	private LocalTime endTime;

	@Column(name = "max_patients")
	private Integer maxPatients = 20;

	@Column(name = "is_available", nullable = false)
	private Boolean isAvailable = true;

	@Column(length = 255)
	private String note;

	public DoctorSchedule(Doctor doctor, String dayOfWeek,
						  LocalTime startTime, LocalTime endTime) {
		this.doctor = doctor;
		this.dayOfWeek = dayOfWeek;
		this.startTime = startTime;
		this.endTime = endTime;
		this.maxPatients = 20;
		this.isAvailable = true;
	}
}
