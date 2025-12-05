// FILE: pom.xml (Maven Dependencies)
/*
<dependencies>
    <!-- Spring Boot Starters -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <!-- Database -->
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- JWT Dependencies -->
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.11.5</version>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-impl</artifactId>
        <version>0.11.5</version>
        <scope>runtime</scope>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-jackson</artifactId>
        <version>0.11.5</version>
        <scope>runtime</scope>
    </dependency>

    <!-- Utilities -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- Testing -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.springframework.security</groupId>
        <artifactId>spring-security-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
*/

// FILE: application.yml
/*
server:
  port: 8080

spring:
  application:
    name: auth-service
  datasource:
    url: jdbc:mysql://mysql-db:3306/auth_db?createDatabaseIfNotExist=true
    username: user
    password: password
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: update # Use 'update' for development, 'none' or 'validate' for production
    show-sql: true
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQLDialect

jwt:
  secret: ThisIsAVeryLongAndSecureSecretKeyForJWTGenerationThatMustBeAtLeast256BitsLong
  expiration: 3600 # 1 hour in seconds
*/

// FILE: Dockerfile
/*
# Use a lightweight JDK image
FROM eclipse-temurin:21-jdk-jammy as builder

# Set working directory
WORKDIR /app

# Copy Maven wrapper and pom.xml
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

# Download dependencies (to leverage Docker cache)
RUN ./mvnw dependency:go-offline

# Copy source code
COPY src src

# Build the application
RUN ./mvnw package -DskipTests

# Final stage: Create the runtime image
FROM eclipse-temurin:21-jre-jammy

# Set working directory
WORKDIR /app

# Copy the built JAR file from the builder stage
COPY --from=builder /app/target/*.jar app.jar

# Expose the port the application runs on
EXPOSE 8080

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
*/

// FILE: docker-compose.yml
/*
version: '3.8'

services:
  mysql-db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: auth_db
      MYSQL_USER: user
      MYSQL_PASSWORD: password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  auth-service:
    build: .
    ports:
      - "8080:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql-db:3306/auth_db
    depends_on:
      mysql-db:
        condition: service_healthy
    restart: always

volumes:
  mysql_data:
*/

// --- START OF JAVA SOURCE CODE ---

package com.example.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Main application class for the Authentication Microservice.
 */
@SpringBootApplication
public class AuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(AuthApplication.class, args);
    }
}

// FILE: com/example/auth/entity/User.java

package com.example.auth.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

/**
 * JPA Entity representing a User in the database.
 */
@Entity
@Table(name = "users")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String email;

    @Column(nullable = false)
    private String password; // Hashed password
}

// FILE: com/example/auth/repository/UserRepository.java

package com.example.auth.repository;

import com.example.auth.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * Repository for User entity operations.
 */
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    /**
     * Finds a user by their email address.
     * @param email The email address (used as username).
     * @return Optional containing the User if found.
     */
    Optional<User> findByEmail(String email);
}

// FILE: com/example/auth/dto/RegisterRequest.java

package com.example.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * DTO for user registration requests.
 */
@Data
public class RegisterRequest {

    @NotBlank(message = "Email is required")
    @Email(message = "Email should be valid")
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 6, message = "Password must be at least 6 characters long")
    private String password;
}

// FILE: com/example/auth/dto/LoginRequest.java

package com.example.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * DTO for user login requests.
 */
@Data
public class LoginRequest {

    @NotBlank(message = "Email is required")
    @Email(message = "Email should be valid")
    private String email;

    @NotBlank(message = "Password is required")
    private String password;
}

// FILE: com/example/auth/dto/AuthResponse.java

package com.example.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * DTO for authentication responses (containing the JWT).
 */
@Data
@AllArgsConstructor
public class AuthResponse {
    private String jwt;
    private String email;
}

// FILE: com/example/auth/util/JwtUtil.java

package com.example.auth.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.JwtException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * Utility class for JWT token creation, validation, and extraction.
 */
@Component
public class JwtUtil {

    private static final Logger log = LoggerFactory.getLogger(JwtUtil.class);

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private long expirationTime; // In seconds

    private SecretKey getSigningKey() {
        byte[] keyBytes = Decoders.BASE64.decode(this.secret);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    /**
     * Generates a JWT token for a given UserDetails.
     * @param userDetails The user details object.
     * @return The generated JWT string.
     */
    public String generateToken(UserDetails userDetails) {
        Map<String, Object> claims = new HashMap<>();
        return createToken(claims, userDetails.getUsername());
    }

    private String createToken(Map<String, Object> claims, String subject) {
        long nowMillis = System.currentTimeMillis();
        Date now = new Date(nowMillis);
        Date expiration = new Date(nowMillis + expirationTime * 1000);

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(subject)
                .setIssuedAt(now)
                .setExpiration(expiration)
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * Validates if the token is valid for the given user.
     * @param token The JWT token.
     * @param userDetails The user details.
     * @return True if the token is valid, false otherwise.
     */
    public boolean validateToken(String token, UserDetails userDetails) {
        final String username = extractUsername(token);
        return (username.equals(userDetails.getUsername()) && !isTokenExpired(token));
    }

    // --- Extraction Methods ---

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    private <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (JwtException e) {
            log.warn("JWT validation failed: {}", e.getMessage());
            throw new JwtException("Invalid JWT token", e);
        }
    }

    private boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }
}

// FILE: com/example/auth/security/UserDetailsServiceImpl.java

package com.example.auth.security;

import com.example.auth.entity.User;
import com.example.auth.repository.UserRepository;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.ArrayList;

/**
 * Custom implementation of Spring Security's UserDetailsService.
 * Loads user details from the database using email as the username.
 */
@Service
public class UserDetailsServiceImpl implements UserDetailsService {

    private final UserRepository userRepository;

    public UserDetailsServiceImpl(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UsernameNotFoundException("User not found with email: " + email));

        // Note: We are using the standard Spring Security User object here.
        // Roles/Authorities are empty for this simple authentication service.
        return new org.springframework.security.core.userdetails.User(
                user.getEmail(),
                user.getPassword(),
                new ArrayList<>()
        );
    }
}

// FILE: com/example/auth/security/JwtRequestFilter.java

package com.example.auth.security;

import com.example.auth.util.JwtUtil;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Filter responsible for extracting and validating JWT tokens from incoming requests.
 */
@Component
public class JwtRequestFilter extends OncePerRequestFilter {

    private final UserDetailsServiceImpl userDetailsService;
    private final JwtUtil jwtUtil;

    public JwtRequestFilter(UserDetailsServiceImpl userDetailsService, JwtUtil jwtUtil) {
        this.userDetailsService = userDetailsService;
        this.jwtUtil = jwtUtil;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        final String authorizationHeader = request.getHeader("Authorization");

        String username = null;
        String jwt = null;

        if (authorizationHeader != null && authorizationHeader.startsWith("Bearer ")) {
            jwt = authorizationHeader.substring(7);
            try {
                username = jwtUtil.extractUsername(jwt);
            } catch (JwtException e) {
                logger.warn("JWT Token is invalid or expired: {}", e.getMessage());
                // Continue chain, but authentication will fail later if required
            }
        }

        // If username is found and no authentication is currently set in context
        if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {

            UserDetails userDetails = this.userDetailsService.loadUserByUsername(username);

            if (jwtUtil.validateToken(jwt, userDetails)) {
                // Create authentication object
                UsernamePasswordAuthenticationToken usernamePasswordAuthenticationToken = new UsernamePasswordAuthenticationToken(
                        userDetails, null, userDetails.getAuthorities());
                
                // Set details (IP, session ID)
                usernamePasswordAuthenticationToken
                        .setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                
                // Set authentication in the context
                SecurityContextHolder.getContext().setAuthentication(usernamePasswordAuthenticationToken);
            }
        }
        chain.doFilter(request, response);
    }
}

// FILE: com/example/auth/security/SecurityConfig.java

package com.example.auth.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Configuration class for Spring Security.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtRequestFilter jwtRequestFilter;

    public SecurityConfig(JwtRequestFilter jwtRequestFilter) {
        this.jwtRequestFilter = jwtRequestFilter;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // Disable CSRF since we are using JWT (stateless)
            .csrf(AbstractHttpConfigurer::disable)
            
            // Configure authorization rules
            .authorizeHttpRequests(auth -> auth
                // Allow registration and login endpoints without authentication
                .requestMatchers("/api/auth/register", "/api/auth/login").permitAll()
                // Require authentication for all other requests
                .anyRequest().authenticated()
            )
            
            // Configure session management to be stateless
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            
            // Add the JWT filter before the standard Spring Security filter
            .addFilterBefore(jwtRequestFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}

// FILE: com/example/auth/service/AuthService.java

package com.example.auth.service;

import com.example.auth.dto.AuthResponse;
import com.example.auth.dto.LoginRequest;
import com.example.auth.dto.RegisterRequest;
import com.example.auth.entity.User;
import com.example.auth.repository.UserRepository;
import com.example.auth.util.JwtUtil;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * Service layer handling user registration and authentication logic.
 */
@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final UserDetailsService userDetailsService;
    private final JwtUtil jwtUtil;

    public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder,
                       AuthenticationManager authenticationManager, UserDetailsService userDetailsService,
                       JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.authenticationManager = authenticationManager;
        this.userDetailsService = userDetailsService;
        this.jwtUtil = jwtUtil;
    }

    /**
     * Registers a new user.
     * @param request Registration details.
     * @return The newly created user entity.
     * @throws IllegalStateException if the email already exists.
     */
    @Transactional
    public User registerUser(RegisterRequest request) {
        Optional<User> existingUser = userRepository.findByEmail(request.getEmail());
        if (existingUser.isPresent()) {
            throw new IllegalStateException("Email already registered: " + request.getEmail());
        }

        User newUser = new User();
        newUser.setEmail(request.getEmail());
        // Hash the password before saving
        newUser.setPassword(passwordEncoder.encode(request.getPassword()));

        return userRepository.save(newUser);
    }

    /**
     * Authenticates a user and generates a JWT token.
     * @param request Login credentials.
     * @return AuthResponse containing the JWT token.
     * @throws AuthenticationException if credentials are invalid.
     */
    public AuthResponse loginUser(LoginRequest request) throws AuthenticationException {
        // 1. Authenticate using Spring Security's AuthenticationManager
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword())
        );

        // 2. Load UserDetails to generate the token
        final UserDetails userDetails = userDetailsService.loadUserByUsername(request.getEmail());

        // 3. Generate JWT
        final String jwt = jwtUtil.generateToken(userDetails);

        return new AuthResponse(jwt, userDetails.getUsername());
    }
}

// FILE: com/example/auth/controller/UserController.java

package com.example.auth.controller;

import com.example.auth.dto.AuthResponse;
import com.example.auth.dto.LoginRequest;
import com.example.auth.dto.RegisterRequest;
import com.example.auth.entity.User;
import com.example.auth.service.AuthService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * REST Controller for user authentication endpoints (Registration and Login).
 */
@RestController
@RequestMapping("/api/auth")
public class UserController {

    private static final Logger log = LoggerFactory.getLogger(UserController.class);

    private final AuthService authService;

    public UserController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * Endpoint for user registration.
     */
    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody RegisterRequest request) {
        try {
            User user = authService.registerUser(request);
            log.info("User registered successfully: {}", user.getEmail());
            return ResponseEntity.status(HttpStatus.CREATED).body(
                    Map.of("message", "User registered successfully", "email", user.getEmail())
            );
        } catch (IllegalStateException e) {
            log.warn("Registration failed: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.CONFLICT).body(
                    Map.of("error", e.getMessage())
            );
        } catch (Exception e) {
            log.error("Unexpected error during registration", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(
                    Map.of("error", "An unexpected error occurred")
            );
        }
    }

    /**
     * Endpoint for user login and JWT generation.
     */
    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        try {
            AuthResponse response = authService.loginUser(request);
            log.info("User logged in successfully: {}", request.getEmail());
            return ResponseEntity.ok(response);
        } catch (AuthenticationException e) {
            log.warn("Login failed for user {}: Invalid credentials", request.getEmail());
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(
                    Map.of("error", "Invalid email or password")
            );
        } catch (Exception e) {
            log.error("Unexpected error during login", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(
                    Map.of("error", "An unexpected error occurred")
            );
        }
    }
    
    /**
     * Example protected endpoint to test JWT functionality.
     */
    @GetMapping("/protected")
    public ResponseEntity<String> protectedResource() {
        return ResponseEntity.ok("This is a protected resource. JWT is valid.");
    }
}

// --- START OF JAVA TEST CODE ---

// FILE: com/example/auth/service/AuthServiceTest.java

package com.example.auth.service;

import com.example.auth.dto.LoginRequest;
import com.example.auth.dto.RegisterRequest;
import com.example.auth.entity.User;
import com.example.auth.repository.UserRepository;
import com.example.auth.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;
    @Mock
    private PasswordEncoder passwordEncoder;
    @Mock
    private AuthenticationManager authenticationManager;
    @Mock
    private UserDetailsService userDetailsService;
    @Mock
    private JwtUtil jwtUtil;

    @InjectMocks
    private AuthService authService;

    private RegisterRequest registerRequest;
    private LoginRequest loginRequest;
    private User user;

    @BeforeEach
    void setUp() {
        registerRequest = new RegisterRequest();
        registerRequest.setEmail("test@example.com");
        registerRequest.setPassword("password123");

        loginRequest = new LoginRequest();
        loginRequest.setEmail("test@example.com");
        loginRequest.setPassword("password123");

        user = new User(1L, "test@example.com", "hashedPassword");
    }

    @Test
    void registerUser_Success() {
        when(userRepository.findByEmail(anyString())).thenReturn(Optional.empty());
        when(passwordEncoder.encode(anyString())).thenReturn("hashedPassword");
        when(userRepository.save(any(User.class))).thenReturn(user);

        User registeredUser = authService.registerUser(registerRequest);

        assertNotNull(registeredUser);
        assertEquals("test@example.com", registeredUser.getEmail());
        assertEquals("hashedPassword", registeredUser.getPassword());
        verify(userRepository, times(1)).save(any(User.class));
    }

    @Test
    void registerUser_EmailAlreadyExists_ThrowsException() {
        when(userRepository.findByEmail(anyString())).thenReturn(Optional.of(user));

        assertThrows(IllegalStateException.class, () -> authService.registerUser(registerRequest));
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void loginUser_Success() {
        UserDetails userDetails = mock(UserDetails.class);
        when(userDetails.getUsername()).thenReturn("test@example.com");

        // Mock AuthenticationManager success
        doNothing().when(authenticationManager).authenticate(any(UsernamePasswordAuthenticationToken.class));
        
        when(userDetailsService.loadUserByUsername(anyString())).thenReturn(userDetails);
        when(jwtUtil.generateToken(userDetails)).thenReturn("mock.jwt.token");

        var response = authService.loginUser(loginRequest);

        assertNotNull(response);
        assertEquals("mock.jwt.token", response.getJwt());
        assertEquals("test@example.com", response.getEmail());
        verify(authenticationManager, times(1)).authenticate(any(UsernamePasswordAuthenticationToken.class));
    }

    @Test
    void loginUser_InvalidCredentials_ThrowsException() {
        // Mock AuthenticationManager failure
        doThrow(new BadCredentialsException("Invalid")).when(authenticationManager).authenticate(any());

        assertThrows(BadCredentialsException.class, () -> authService.loginUser(loginRequest));
        verify(userDetailsService, never()).loadUserByUsername(anyString());
    }
}

// FILE: com/example/auth/controller/UserControllerTest.java

package com.example.auth.controller;

import com.example.auth.dto.AuthResponse;
import com.example.auth.dto.LoginRequest;
import com.example.auth.dto.RegisterRequest;
import com.example.auth.entity.User;
import com.example.auth.service.AuthService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

// Import necessary security configuration components for the test context
@WebMvcTest(UserController.class)
@Import({com.example.auth.security.SecurityConfig.class, com.example.auth.security.JwtRequestFilter.class})
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private AuthService authService;

    // Mock beans required by SecurityConfig/JwtRequestFilter but not directly tested here
    @MockBean private com.example.auth.security.UserDetailsServiceImpl userDetailsService;
    @MockBean private com.example.auth.util.JwtUtil jwtUtil;

    private final String BASE_URL = "/api/auth";

    @Test
    void register_Success() throws Exception {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("newuser@test.com");
        request.setPassword("securepass");

        User registeredUser = new User(2L, "newuser@test.com", "hashed");
        when(authService.registerUser(any(RegisterRequest.class))).thenReturn(registeredUser);

        mockMvc.perform(post(BASE_URL + "/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.email").value("newuser@test.com"));
    }

    @Test
    void register_Conflict() throws Exception {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("existing@test.com");
        request.setPassword("securepass");

        doThrow(new IllegalStateException("Email already registered"))
                .when(authService).registerUser(any(RegisterRequest.class));

        mockMvc.perform(post(BASE_URL + "/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error").value("Email already registered"));
    }

    @Test
    void login_Success() throws Exception {
        LoginRequest request = new LoginRequest();
        request.setEmail("user@test.com");
        request.setPassword("password");

        AuthResponse response = new AuthResponse("mock.jwt.token", "user@test.com");
        when(authService.loginUser(any(LoginRequest.class))).thenReturn(response);

        mockMvc.perform(post(BASE_URL + "/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.jwt").value("mock.jwt.token"));
    }

    @Test
    void login_Unauthorized() throws Exception {
        LoginRequest request = new LoginRequest();
        request.setEmail("wrong@test.com");
        request.setPassword("wrongpass");

        doThrow(new BadCredentialsException("Invalid credentials"))
                .when(authService).loginUser(any(LoginRequest.class));

        mockMvc.perform(post(BASE_URL + "/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error").value("Invalid email or password"));
    }
    
    @Test
    @WithMockUser(username = "testuser")
    void protectedResource_Authenticated() throws Exception {
        // Since we use @WithMockUser, Spring Security bypasses the JWT filter 
        // and sets up a valid authentication context.
        mockMvc.perform(get(BASE_URL + "/protected"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").value("This is a protected resource. JWT is valid."));
    }

    @Test
    void protectedResource_Unauthenticated() throws Exception {
        // No @WithMockUser, so the request is unauthenticated
        mockMvc.perform(get(BASE_URL + "/protected"))
                .andExpect(status().isForbidden()); // 403 Forbidden (or 401 Unauthorized depending on configuration)
    }
}