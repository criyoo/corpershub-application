# Non-Functional Requirements Document

## 1. Purpose

This document defines the quality attributes and operational expectations for Corpershub.

## 2. Performance

### 2.1 API Performance Targets

- p95 response time for authenticated list and detail APIs should be 2 seconds or less under normal operating load
- p95 response time for login, registration, and OTP submission should be 3 seconds or less excluding external email latency
- payment status polling endpoints should return in 2 seconds or less for normal provider states

### 2.2 Realtime Performance Targets

- WebSocket connection setup should complete within 3 seconds for authenticated users
- new chat messages should appear to connected participants within 2 seconds end-to-end under normal network conditions
- typing events should propagate within 1 second for active conversations

### 2.3 Search and Pagination

- directory list APIs shall paginate results at a default page size of 12
- search and filter operations shall remain index-backed for core fields such as role, location, study field, degree, university, and status

## 3. Scalability

- the application shall support horizontal scaling of frontend, backend, and worker processes
- the application shall support separate Redis, PostgreSQL, and object storage services
- chat workloads shall scale by Redis-backed channel layers
- background work shall scale by running multiple Celery workers

## 4. Availability

- target service availability should be at least 99.5% monthly for the production environment
- the system should degrade gracefully when optional subsystems such as async email dispatch are unavailable
- payment webhook processing failures shall not corrupt persisted payment state

## 5. Reliability

- PostgreSQL shall remain the system of record for accounts, profiles, interests, conversations, audit logs, verification attempts, subscriptions, and payments
- the platform shall use idempotency-oriented transaction references and webhook event persistence for payment flows
- message history shall remain durable after service restarts
- audit history shall remain durable after service restarts

## 6. Security

### 6.1 Authentication and Authorization

- protected API endpoints shall require authentication by default
- role-based permission checks shall be enforced for company, student, and admin endpoints
- JWT bearer tokens shall be used for stateless API authorization
- WebSocket connections shall only be accepted for authenticated and authorized conversation participants

### 6.2 Sensitive Data Protection

- NIN shall be encrypted at rest
- NIN and NYSC call-up values shall be hashed for duplicate detection without exposing raw comparison values
- masked forms of sensitive values shall be used in admin and workflow responses where appropriate
- company contact details and student sensitive identifiers shall not be exposed indiscriminately in public discovery flows

### 6.3 Payment Security

- webhook signatures shall be verified when secrets are configured
- payment transaction references and webhook events shall be persisted for reconciliation
- reactivation tokens shall be signed and time-bound

### 6.4 Production Hardening

- production shall not use permissive development defaults such as wildcard hosts or open CORS
- production secrets shall be injected through environment configuration
- TLS termination shall be enforced at the edge or load balancer

## 7. Usability

- the UI shall provide distinct navigation and task flows for company, student, and admin roles
- onboarding copy shall make role purpose clear
- error messages shall be actionable but not leak sensitive state
- billing and reactivation flows shall clearly communicate subscription status

## 8. Accessibility

- the frontend should remain keyboard-navigable for primary workflows
- text contrast should meet WCAG AA where feasible in production themes
- form errors should be presented in readable inline or toast feedback

## 9. Maintainability

- the backend shall remain organized as a modular monolith with clear app boundaries
- the frontend shall remain structured by route and shared component libraries
- API schemas shall remain discoverable via OpenAPI endpoints
- business rules should be encapsulated in services and serializers rather than scattered across views

## 10. Observability

- audit logs shall capture sensitive operational events
- payment webhook events shall be persisted for operational tracing
- admin overview counts shall provide basic operational visibility
- production deployment should include centralized logging and metrics aggregation even though these are not fully built into the repo

## 11. Backup and Disaster Recovery

### 11.1 Backup Requirements

- PostgreSQL backups shall be performed at least daily
- media storage shall be backed up or versioned according to deployment policy
- webhook and audit records shall be included in database backups

### 11.2 Recovery Targets

- target RPO should be 24 hours or better
- target RTO should be 4 hours or better for a standard production deployment

## 12. Localization

- current implementation is English-first and Nigeria-specific
- locale-sensitive formatting shall support Nigerian currency and date formats where billing is displayed
- phone validation and business rules shall remain aligned to Nigerian usage patterns

## 13. Compliance and Auditability

- the system shall maintain event-level records for auth, verification, interest, chat initiation, payment, and reactivation actions
- admin actions shall be limited to authorized users
- verification reviews shall preserve reviewer identity and review notes

## 14. Capacity and Concurrency Assumptions

- the system should support at least low-thousands of registered users and concurrent browsing in the initial production phase
- the system should support hundreds of simultaneous active chat connections when Redis and ASGI services are provisioned correctly
- exact concurrency limits depend on deployment sizing and are not proven by the repo alone

## 15. File and Media Constraints

- profile photo and company image uploads shall be limited to 3 MB
- supported image formats shall be JPG, JPEG, PNG, and WebP
- media storage paths shall keep company and student assets logically separated

## 16. Known Current Constraints

- Redis is configured for channels and Celery but application-level read caching is minimal
- Celery infrastructure exists but current background-job usage is narrow
- company billing support still exists in backend billing code even though company dashboard billing has been removed from the active UX

## 17. Summary

Corpershub’s non-functional requirements emphasize privacy, role-based access, operational auditability, reliable chat, and deployment readiness for a production-grade Nigerian marketplace. Production environments must apply stricter security and operational controls than the repository’s default development setup.
