"""Project templates for multi-file scaffolding."""

from typing import Dict, List

# Template definitions: name -> structure, files, dependencies, commands
PROJECT_TEMPLATES = {
    "fastapi": {
        "name": "FastAPI REST API",
        "description": "FastAPI REST API with SQLAlchemy models, Pydantic schemas, and pytest",
        "language": "python",
        "structure": {
            "src": {
                "main.py": "# Main FastAPI app",
                "models.py": "# SQLAlchemy models",
                "schemas.py": "# Pydantic schemas",
                "database.py": "# Database config",
                "crud.py": "# CRUD operations",
                "config.py": "# Configuration",
            },
            "tests": {
                "test_main.py": "# Main API tests",
                "conftest.py": "# Pytest fixtures",
            },
        },
        "config_files": {
            ".gitignore": """__pycache__/
*.py[cod]
*$py.class
*.so
.venv/
venv/
env/
.env
.env.local
.DS_Store
""",
            "requirements.txt": """fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
""",
            "Dockerfile": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
            ".github/workflows/ci.yml": """name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest
""",
            "README.md": """# FastAPI Application

## Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn src.main:app --reload
```

## Test
```bash
pytest
```
""",
        },
        "python_version": "3.11",
        "entrypoint": "src.main:app",
    },
    "spring_boot": {
        "name": "Spring Boot REST API",
        "description": "Spring Boot REST API with JPA and basic CRUD operations",
        "language": "java",
        "structure": {
            "src/main/java/com/example": {
                "controller": "# REST controllers",
                "service": "# Business logic",
                "model": "# JPA entities",
                "repository": "# Data access",
                "config": "# Configuration classes",
            },
            "src/main/resources": {
                "application.yml": "# Spring config",
            },
            "src/test/java/com/example": {
                "controller": "# Controller tests",
                "service": "# Service tests",
            },
        },
        "config_files": {
            "pom.xml": """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.1.5</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>microservice</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <!-- Use MariaDB JDBC driver as a compatible, widely-available replacement -->
        <dependency>
            <groupId>org.mariadb.jdbc</groupId>
            <artifactId>mariadb-java-client</artifactId>
            <version>3.1.4</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>0.12.3</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>21</source>
                    <target>21</target>
                    <forceJavacCompilerUse>true</forceJavacCompilerUse>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
""",
            "Dockerfile": """FROM maven:3.9.5-eclipse-temurin-21 as builder
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests
FROM eclipse-temurin:21-jre
COPY --from=builder /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
""",
            "docker-compose.yml": """version: "3.8"
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: appdb
    ports:
      - "3306:3306"
  app:
    build: .
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/appdb
      SPRING_DATASOURCE_USERNAME: root
      SPRING_DATASOURCE_PASSWORD: root
    ports:
      - "8080:8080"
    depends_on:
      - mysql
""",
            ".gitignore": """target/
.mvn/
mvnw
mvnw.cmd
*.jar
*.class
.DS_Store
.idea/
*.iml
""",
            "README.md": """# Spring Boot Microservice

## Build
```bash
mvn clean package
```

## Run
```bash
java -jar target/microservice-1.0.0.jar
```

## Docker
```bash
docker-compose up
```
""",
        },
        "java_version": "21",
        "build_tool": "maven",
    },
    "python_package": {
        "name": "Python Package",
        "description": "Generic Python package with setup.py, pytest, and documentation",
        "language": "python",
        "structure": {
            "src": {
                "main.py": "# Main module",
                "utils.py": "# Utility functions",
                "__init__.py": "# Package init",
            },
            "tests": {
                "test_main.py": "# Main tests",
                "conftest.py": "# Test config",
                "__init__.py": "",
            },
            "docs": {
                "index.md": "# Documentation",
            },
        },
        "config_files": {
            "setup.py": """from setuptools import setup, find_packages

setup(
    name="mypackage",
    version="0.1.0",
    description="A Python package",
    author="Generated by Agentic Code Studio",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0", "black", "flake8"],
    },
)
""",
            "pyproject.toml": """[build-system]
requires = ["setuptools>=65", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mypackage"
version = "0.1.0"
description = "A Python package"
requires-python = ">=3.9"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7.0", "black", "flake8"]
""",
            "requirements.txt": """pytest>=7.0
black>=23.0
flake8>=6.0
""",
            ".gitignore": """__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.DS_Store
""",
            "README.md": """# My Python Package

## Installation
```bash
pip install -e .
```

## Development
```bash
pip install -e ".[dev]"
pytest
```
""",
        },
        "python_version": "3.11",
    },
}

# Template categories
TEMPLATE_CATEGORIES = {
    "web": ["fastapi"],
    "backend": ["spring_boot"],
    "library": ["python_package"],
}


def get_template(template_name: str) -> Dict:
    """Get template by name."""
    return PROJECT_TEMPLATES.get(template_name)


def list_templates() -> List[Dict]:
    """List all available templates as metadata dicts.

    Returns a list of dicts with keys: `key`, `name`, `description`, and `language`.
    This is suitable for UI display and future metadata extensions.
    """
    templates = []
    for key, tpl in PROJECT_TEMPLATES.items():
        templates.append(
            {
                "key": key,
                "name": tpl.get("name", key),
                "description": tpl.get("description", ""),
                "language": tpl.get("language"),
            }
        )
    return templates


def get_template_by_language(language: str) -> List[str]:
    """Get templates for a specific language."""
    return [
        name
        for name, template in PROJECT_TEMPLATES.items()
        if template.get("language") == language
    ]
