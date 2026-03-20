package com.sample.llm.service;

import com.sample.llm.dto.DoctorDto;
import com.sample.llm.dto.DoctorWithScheduleDto;
import com.sample.llm.entity.Doctor;
import com.sample.llm.entity.DoctorSchedule;
import com.sample.llm.repository.DoctorRepository;
import com.sample.llm.repository.DoctorScheduleRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DoctorServiceTest {

	@Mock
	private DoctorRepository doctorRepository;

	@Mock
	private DoctorScheduleRepository doctorScheduleRepository;

	@InjectMocks
	private DoctorService doctorService;

	@Test
	@DisplayName("진료과명으로 의사 목록 조회")
	void findDoctorsByDepartment() {
		// given
		Doctor d1 = new Doctor("김정형", "정형외과", null, "관절외과", "서울대학교병원");
		d1.setId(1L);
		Doctor d2 = new Doctor("이관절", "정형외과", null, "척추외과", "세브란스병원");
		d2.setId(2L);

		when(doctorRepository.findByDepartmentAndIsActiveTrue("정형외과"))
				.thenReturn(List.of(d1, d2));

		// when
		List<DoctorDto> result = doctorService.findDoctorsByDepartment("정형외과");

		// then
		assertThat(result).hasSize(2);
		assertThat(result.get(0).getName()).isEqualTo("김정형");
		assertThat(result.get(1).getName()).isEqualTo("이관절");
	}

	@Test
	@DisplayName("공백이 포함된 진료과명 정규화")
	void findDoctorsByDepartment_normalizedName() {
		// given
		when(doctorRepository.findByDepartmentAndIsActiveTrue("정형외과"))
				.thenReturn(List.of());

		// when: "정형 외과" → "정형외과"로 정규화
		List<DoctorDto> result = doctorService.findDoctorsByDepartment("정형 외과");

		// then
		assertThat(result).isEmpty();
	}

	@Test
	@DisplayName("의사 + 스케줄 포함 조회")
	void findDoctorsWithSchedule() {
		// given
		Doctor doctor = new Doctor("김정형", "정형외과", null, "관절외과", "서울대학교병원");
		doctor.setId(1L);

		DoctorSchedule schedule = new DoctorSchedule(
				doctor, "MON", LocalTime.of(9, 0), LocalTime.of(17, 0));

		when(doctorRepository.findByDepartmentAndIsActiveTrue("정형외과"))
				.thenReturn(List.of(doctor));
		when(doctorScheduleRepository.findByDoctorIdInAndIsAvailableTrue(List.of(1L)))
				.thenReturn(List.of(schedule));

		// when
		List<DoctorWithScheduleDto> result = doctorService.findDoctorsWithSchedule("정형외과");

		// then
		assertThat(result).hasSize(1);
		assertThat(result.get(0).getName()).isEqualTo("김정형");
		assertThat(result.get(0).getSchedules()).hasSize(1);
		assertThat(result.get(0).getSchedules().get(0).getDayOfWeek()).isEqualTo("MON");
	}

	@Test
	@DisplayName("존재하지 않는 진료과 조회 시 빈 목록")
	void findDoctorsByDepartment_notFound() {
		// given
		when(doctorRepository.findByDepartmentAndIsActiveTrue("존재하지않는과"))
				.thenReturn(List.of());

		// when
		List<DoctorDto> result = doctorService.findDoctorsByDepartment("존재하지않는과");

		// then
		assertThat(result).isEmpty();
	}
}
