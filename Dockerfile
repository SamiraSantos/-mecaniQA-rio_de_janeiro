# syntax=docker/dockerfile:1

# Compila a API em uma etapa separada para não levar o Maven para a imagem final.
FROM maven:3.9-eclipse-temurin-17-alpine AS build

WORKDIR /workspace

COPY pom.xml .
RUN mvn -B dependency:go-offline

COPY src ./src
RUN mvn -B clean package -DskipTests

# Imagem definida pela equipe para executar a aplicação com Java 17.
FROM eclipse-temurin:17-jdk-alpine

WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=build --chown=appuser:appgroup /workspace/target/mecaniqa-api.jar /app/app.jar

USER appuser

EXPOSE 8080

# O processo Java fica em primeiro plano e mantém o container em execução.
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
