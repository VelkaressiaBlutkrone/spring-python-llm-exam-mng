package com.sample.llm.repository;

import com.sample.llm.entity.MedicalContent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MedicalContentRepository extends JpaRepository<MedicalContent, Long> {

	List<MedicalContent> findByDomainAndLanguage(Integer domain, String language);

	@Query(value = "SELECT * FROM medical_content "
			+ "WHERE MATCH(content) AGAINST(:keyword IN BOOLEAN MODE) "
			+ "LIMIT :limit",
			nativeQuery = true)
	List<MedicalContent> searchByContent(@Param("keyword") String keyword,
			@Param("limit") int limit);
}
