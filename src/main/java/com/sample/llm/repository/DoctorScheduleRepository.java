package com.sample.llm.repository;

import com.sample.llm.entity.DoctorSchedule;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DoctorScheduleRepository extends JpaRepository<DoctorSchedule, Long> {

	List<DoctorSchedule> findByDoctorIdAndIsAvailableTrue(Long doctorId);

	List<DoctorSchedule> findByDoctorDepartmentAndDayOfWeekAndIsAvailableTrue(
			String department, String dayOfWeek);
}
