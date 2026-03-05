package com.sample.llm.repository;

import com.sample.llm.entity.ChatHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatHistoryRepository extends JpaRepository<ChatHistory, Long> {

	Page<ChatHistory> findByUser_IdOrderByTimestampDesc(Long userId, Pageable pageable);
}
