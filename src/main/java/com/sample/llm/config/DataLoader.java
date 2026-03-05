package com.sample.llm.config;

import com.sample.llm.entity.User;
import com.sample.llm.repository.UserRepository;
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

	private final UserRepository userRepository;

	@Override
	public void run(ApplicationArguments args) {
		if (userRepository.count() == 0) {
			userRepository.save(new User("default", "default@example.com"));
			log.info("초기 사용자 시드 데이터 생성 완료");
		}
	}
}
