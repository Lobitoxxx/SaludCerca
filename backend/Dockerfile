# Imagen de la API SaludCerca (Spring Boot, jar ya compilado con Maven local)
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY target/backend-1.0.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
