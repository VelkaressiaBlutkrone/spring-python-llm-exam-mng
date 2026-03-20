package com.sample.llm.config;

import com.sample.llm.entity.Doctor;
import com.sample.llm.entity.DoctorSchedule;
import com.sample.llm.entity.MedicalDomain;
import com.sample.llm.entity.Staff;
import com.sample.llm.repository.DoctorRepository;
import com.sample.llm.repository.DoctorScheduleRepository;
import com.sample.llm.repository.MedicalDomainRepository;
import com.sample.llm.repository.StaffRepository;

import java.time.LocalTime;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("!test")
@RequiredArgsConstructor
@Slf4j
public class DataLoader implements ApplicationRunner {

	private final StaffRepository staffRepository;
	private final DoctorRepository doctorRepository;
	private final DoctorScheduleRepository doctorScheduleRepository;
	private final MedicalDomainRepository medicalDomainRepository;

	@Override
	public void run(ApplicationArguments args) {
		if (staffRepository.count() == 0) {
			staffRepository.save(new Staff("default", "default@example.com"));
			log.info("초기 직원(Staff) 시드 데이터 생성 완료");
		}

		if (doctorRepository.count() == 0) {
			loadDoctorSeedData();
			log.info("초기 의사/스케줄 시드 데이터 생성 완료");
		}
	}

	private void loadDoctorSeedData() {
		// 도메인 조회 (없으면 null로 설정)
		MedicalDomain orthopedics = medicalDomainRepository.findByDomainName("정형외과").orElse(null);
		MedicalDomain neurology = medicalDomainRepository.findByDomainName("신경과").orElse(null);
		MedicalDomain internalMed = medicalDomainRepository.findByDomainName("내과").orElse(null);
		MedicalDomain dermatology = medicalDomainRepository.findByDomainName("피부과").orElse(null);

		// 정형외과 의사
		Doctor d1 = doctorRepository.save(new Doctor("김정형", "정형외과", orthopedics, "관절외과", "서울대학교병원"));
		Doctor d2 = doctorRepository.save(new Doctor("이관절", "정형외과", orthopedics, "척추외과", "세브란스병원"));
		Doctor d3 = doctorRepository.save(new Doctor("박뼈대", "정형외과", orthopedics, "스포츠의학", "삼성서울병원"));

		// 신경과 의사
		Doctor d4 = doctorRepository.save(new Doctor("최신경", "신경과", neurology, "두통클리닉", "서울아산병원"));
		Doctor d5 = doctorRepository.save(new Doctor("정뇌과", "신경과", neurology, "뇌졸중", "고려대병원"));

		// 내과 의사
		Doctor d6 = doctorRepository.save(new Doctor("한내과", "내과", internalMed, "소화기내과", "서울대학교병원"));
		Doctor d7 = doctorRepository.save(new Doctor("윤심장", "내과", internalMed, "순환기내과", "세브란스병원"));

		// 피부과 의사
		Doctor d8 = doctorRepository.save(new Doctor("서피부", "피부과", dermatology, "알레르기", "강남세브란스"));
		Doctor d9 = doctorRepository.save(new Doctor("임아토", "피부과", dermatology, "아토피클리닉", "삼성서울병원"));

		// 스케줄 등록
		addSchedule(d1, "MON", 9, 17);
		addSchedule(d1, "WED", 9, 17);
		addSchedule(d1, "FRI", 9, 17);

		addSchedule(d2, "TUE", 9, 12);
		addSchedule(d2, "THU", 9, 12);

		addSchedule(d3, "MON", 13, 17);
		addSchedule(d3, "WED", 13, 17);
		addSchedule(d3, "FRI", 13, 17);

		addSchedule(d4, "MON", 9, 17);
		addSchedule(d4, "TUE", 9, 17);
		addSchedule(d4, "THU", 9, 17);

		addSchedule(d5, "WED", 9, 12);
		addSchedule(d5, "FRI", 9, 12);

		addSchedule(d6, "MON", 9, 17);
		addSchedule(d6, "WED", 9, 17);

		addSchedule(d7, "TUE", 9, 17);
		addSchedule(d7, "THU", 9, 17);

		addSchedule(d8, "MON", 10, 16);
		addSchedule(d8, "WED", 10, 16);
		addSchedule(d8, "FRI", 10, 16);

		addSchedule(d9, "TUE", 9, 13);
		addSchedule(d9, "THU", 9, 13);
	}

	private void addSchedule(Doctor doctor, String dayOfWeek, int startHour, int endHour) {
		doctorScheduleRepository.save(new DoctorSchedule(
				doctor, dayOfWeek,
				LocalTime.of(startHour, 0),
				LocalTime.of(endHour, 0)
		));
	}
}
