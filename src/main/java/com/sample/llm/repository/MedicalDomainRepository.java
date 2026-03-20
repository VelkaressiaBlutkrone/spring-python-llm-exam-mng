package com.sample.llm.repository;

import com.sample.llm.entity.MedicalDomain;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface MedicalDomainRepository extends JpaRepository<MedicalDomain, Integer> {

	Optional<MedicalDomain> findByDomainName(String domainName);
}
