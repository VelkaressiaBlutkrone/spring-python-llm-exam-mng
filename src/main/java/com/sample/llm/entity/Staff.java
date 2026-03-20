package com.sample.llm.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * ERD v4.0 STAFF 테이블 매핑.
 * 병원 내부 직원(로그인 계정). CHATBOT_HISTORY의 staff_id FK 참조.
 */
@Entity
@Table(name = "staff")
@Getter
@Setter
@NoArgsConstructor
public class Staff {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(nullable = false, length = 100)
	private String username;

	@Column(name = "employee_number", length = 20, unique = true)
	private String employeeNumber;

	@Column(nullable = false, length = 255)
	private String email;

	public Staff(String username, String email) {
		this.username = username;
		this.email = email;
	}
}
