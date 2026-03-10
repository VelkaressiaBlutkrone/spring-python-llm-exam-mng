package com.sample.llm.repository;

import com.sample.llm.entity.ChatbotHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatbotHistoryRepository extends JpaRepository<ChatbotHistory, Long> {

	Page<ChatbotHistory> findByStaff_IdOrderByCreatedAtDesc(Long staffId, Pageable pageable);
}
