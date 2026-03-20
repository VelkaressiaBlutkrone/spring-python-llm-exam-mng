package com.sample.llm.repository;

import com.sample.llm.entity.Doctor;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DoctorRepository extends JpaRepository<Doctor, Long> {

	List<Doctor> findByDepartmentAndIsActiveTrue(String department);

	List<Doctor> findByMedicalDomainDomainIdAndIsActiveTrue(Integer domainId);
}
