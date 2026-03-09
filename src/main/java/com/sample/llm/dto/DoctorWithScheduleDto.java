package com.sample.llm.dto;

import com.sample.llm.entity.Doctor;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
public class DoctorWithScheduleDto {

	private Long id;
	private String name;
	private String department;
	private String specialty;
	private String hospital;
	private String phone;
	private String email;
	private String bio;
	private List<DoctorScheduleDto> schedules;

	public static DoctorWithScheduleDto from(Doctor entity, List<DoctorScheduleDto> schedules) {
		return new DoctorWithScheduleDto(
				entity.getId(),
				entity.getName(),
				entity.getDepartment(),
				entity.getSpecialty(),
				entity.getHospital(),
				entity.getPhone(),
				entity.getEmail(),
				entity.getBio(),
				schedules
		);
	}
}
