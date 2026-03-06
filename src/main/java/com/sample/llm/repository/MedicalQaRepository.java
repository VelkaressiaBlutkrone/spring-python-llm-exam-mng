package com.sample.llm.repository;

import com.sample.llm.entity.MedicalQa;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MedicalQaRepository extends JpaRepository<MedicalQa, Long> {

	List<MedicalQa> findByDepartment(String department);

	@Query(value = "SELECT * FROM medical_qa "
			+ "WHERE MATCH(question) AGAINST(:keyword IN BOOLEAN MODE) "
			+ "LIMIT :limit",
			nativeQuery = true)
	List<MedicalQa> searchByQuestion(@Param("keyword") String keyword,
			@Param("limit") int limit);
}
