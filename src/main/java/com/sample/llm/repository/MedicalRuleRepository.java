package com.sample.llm.repository;

import com.sample.llm.entity.MedicalRule;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MedicalRuleRepository extends JpaRepository<MedicalRule, Integer> {

	List<MedicalRule> findByCategory(String category);
}
