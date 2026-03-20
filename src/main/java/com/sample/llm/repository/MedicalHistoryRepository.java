package com.sample.llm.repository;

import com.sample.llm.entity.MedicalHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MedicalHistoryRepository extends JpaRepository<MedicalHistory, Long> {

	Page<MedicalHistory> findByStaff_IdOrderByCreatedAtDesc(Long staffId, Pageable pageable);
}
