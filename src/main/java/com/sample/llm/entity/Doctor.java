package com.sample.llm.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "doctor")
@Getter
@Setter
@NoArgsConstructor
public class Doctor {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, length = 50)
	private String name;

	@Column(nullable = false, length = 50)
	private String department;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "domain_id")
	private MedicalDomain medicalDomain;

	@Column(length = 100)
	private String specialty;

	@Column(nullable = false, length = 100)
	private String hospital;

	@Column(length = 20)
	private String phone;

	@Column(length = 255)
	private String email;

	@Column(columnDefinition = "TEXT")
	private String bio;

	@Column(name = "is_active", nullable = false)
	private Boolean isActive = true;

	@Column(name = "created_at", nullable = false)
	private LocalDateTime createdAt;

	public Doctor(String name, String department, MedicalDomain medicalDomain,
				  String specialty, String hospital) {
		this.name = name;
		this.department = department;
		this.medicalDomain = medicalDomain;
		this.specialty = specialty;
		this.hospital = hospital;
		this.isActive = true;
		this.createdAt = LocalDateTime.now();
	}
}
