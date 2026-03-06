package com.sample.llm.config;

import io.netty.channel.ChannelOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;

@Configuration
public class WebClientConfig {

	@Value("${llm.service.url}")
	private String llmServiceUrl;

	@Value("${llm.service.timeout.connect:5000}")
	private int connectTimeout;

	@Value("${llm.service.timeout.read:60000}")
	private int readTimeout;

	@Bean
	public WebClient llmWebClient() {
		HttpClient httpClient = HttpClient.create()
			.responseTimeout(Duration.ofMillis(readTimeout))
			.option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeout);

		return WebClient.builder()
			.baseUrl(llmServiceUrl)
			.clientConnector(new ReactorClientHttpConnector(httpClient))
			.build();
	}
}
