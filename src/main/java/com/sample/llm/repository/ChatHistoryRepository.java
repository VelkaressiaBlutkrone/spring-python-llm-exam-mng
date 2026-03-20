package com.sample.llm.repository;

import com.sample.llm.entity.ChatHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatHistoryRepository extends JpaRepository<ChatHistory, Long> {

	Page<ChatHistory> findByStaff_IdOrderByCreatedAtDesc(Long staffId, Pageable pageable);

	Page<ChatHistory> findByStaff_IdAndSessionIdOrderByCreatedAtAsc(Long staffId, String sessionId, Pageable pageable);
}
