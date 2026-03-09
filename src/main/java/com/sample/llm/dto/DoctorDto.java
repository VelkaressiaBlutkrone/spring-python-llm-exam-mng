package com.sample.llm.dto;

import com.sample.llm.entity.Doctor;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class DoctorDto {

	private Long id;
	private String name;
	private String department;
	private String specialty;
	private String hospital;

	public static DoctorDto from(Doctor entity) {
		return new DoctorDto(
				entity.getId(),
				entity.getName(),
				entity.getDepartment(),
				entity.getSpecialty(),
				entity.getHospital()
		);
	}
}
