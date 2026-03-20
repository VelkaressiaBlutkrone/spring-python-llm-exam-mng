# Spring Boot LLM 관리 서버
# 빌드: docker compose build spring-app
# 단독: docker build -t spring-llm-app .

FROM eclipse-temurin:21-jdk AS build

WORKDIR /app

# Gradle wrapper & 설정 복사 (캐시 레이어)
COPY gradlew settings.gradle build.gradle ./
COPY gradle/ gradle/
RUN chmod +x gradlew && ./gradlew dependencies --no-daemon || true

# 소스 복사 & 빌드
COPY src/ src/
RUN ./gradlew bootJar --no-daemon -x test

# 실행 이미지
FROM eclipse-temurin:21-jre

WORKDIR /app

COPY --from=build /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
