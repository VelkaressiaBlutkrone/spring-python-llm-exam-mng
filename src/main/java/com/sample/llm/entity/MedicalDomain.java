package com.sample.llm.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "medical_domain")
@Getter
@Setter
@NoArgsConstructor
public class MedicalDomain {

	@Id
	@Column(name = "domain_id")
	private Integer domainId;

	@Column(name = "domain_name", nullable = false, length = 50)
	private String domainName;

	public MedicalDomain(Integer domainId, String domainName) {
		this.domainId = domainId;
		this.domainName = domainName;
	}
}
