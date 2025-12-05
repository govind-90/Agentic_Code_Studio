FROM maven:3.9.5-eclipse-temurin-21 as builder
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests
FROM eclipse-temurin:21-jre
COPY --from=builder /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
