package com.sample.llm.service;

import com.sample.llm.dto.DoctorDto;
import com.sample.llm.dto.DoctorScheduleDto;
import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.entity.Doctor;
import com.sample.llm.repository.DoctorRepository;
import com.sample.llm.repository.DoctorScheduleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
@Transactional(readOnly = true)
public class DoctorService {

	private final DoctorRepository doctorRepository;
	private final DoctorScheduleRepository doctorScheduleRepository;

	/**
	 * 진료과명으로 활동 중인 의사 목록을 조회한다.
	 * 진료과명은 정규화하여 매칭한다 (공백 제거).
	 */
	public List<DoctorDto> findDoctorsByDepartment(String department) {
		String normalized = normalizeDepartment(department);
		List<Doctor> doctors = doctorRepository.findByDepartmentAndIsActiveTrue(normalized);

		if (doctors.isEmpty()) {
			log.info("No doctors found for department: {}", normalized);
		}

		return doctors.stream()
				.map(DoctorDto::from)
				.toList();
	}

	/**
	 * 진료과명으로 의사 목록 + 스케줄을 함께 조회한다.
	 */
	public List<DoctorWithScheduleDto> findDoctorsWithSchedule(String department) {
		String normalized = normalizeDepartment(department);
		List<Doctor> doctors = doctorRepository.findByDepartmentAndIsActiveTrue(normalized);

		return doctors.stream()
				.map(doctor -> {
					List<DoctorScheduleDto> schedules = doctorScheduleRepository
							.findByDoctorIdAndIsAvailableTrue(doctor.getId())
							.stream()
							.map(DoctorScheduleDto::from)
							.toList();
					return DoctorWithScheduleDto.from(doctor, schedules);
				})
				.toList();
	}

	/**
	 * 진료과명 정규화: 공백 제거, 앞뒤 trim
	 * 예: "정형 외과" → "정형외과"
	 */
	private String normalizeDepartment(String department) {
		if (department == null) {
			return "";
		}
		return department.replaceAll("\\s+", "").trim();
	}
}
