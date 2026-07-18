# Software Architecture Document

## 1. Purpose

This document describes the internal software structure of Corpershub beyond the high-level deployment view.

## 2. Architectural Style

Corpershub uses a modular-monolith architecture:

- one primary backend codebase
- one primary frontend codebase
- domain separation through Django apps and route-grouped frontend areas
- shared persistence layer
- synchronous REST workflows with targeted asynchronous and realtime extensions

This approach keeps implementation simple while preserving clear domain boundaries.

## 3. Backend Bounded Contexts

| Domain | Responsibility |
| --- | --- |
| `accounts` | registration, OTP, login, settings, lifecycle, presence |
| `companies` | company profile aggregate and admin access |
| `students` | corper profile aggregate and admin access |
| `search` | filtering, recommendations, directory statistics |
| `interests` | intent tracking between companies and corpers |
| `chat` | conversation and message lifecycle |
| `notifications` | persistent in-app notifications |
| `verification` | reviewable verification attempts |
| `subscriptions` | plan and subscription lifecycle |
| `payments` | transaction and webhook processing |
| `adminpanel` | internal operational APIs |
| `audit` | event audit trail |

## 4. Core Domain Models

### 4.1 Accounts

- `User`
- `PendingSignup`
- `EmailOTP`
- `EmailDomainRule`
- `UserRoleRegistrationTotal`

### 4.2 Company Side

- `CompanyProfile`

### 4.3 Corper Side

- `StudentProfile`
- `VerificationAttempt`

### 4.4 Marketplace Interaction

- `Interest`
- `Conversation`
- `Message`
- `Notification`

### 4.5 Commercial Domain

- `SubscriptionPlan`
- `UserSubscription`
- `PaymentTransaction`
- `PaymentWebhookEvent`

### 4.6 Governance

- `AuditLog`
- `PlatformOption`

## 5. Frontend Module Design

The frontend is organized by route responsibility and shared component libraries:

- `src/app/*` for route entry points
- `src/components/*` for reusable UI and feature composites
- `src/lib/*` for client utilities, API helpers, billing utilities, nav models, and data formatters
- `src/hooks/*` for client data-fetch helpers such as API query wrappers

Role-specific route clusters mirror the backend permission model:

- `/company/*`
- `/student/*`
- `/admin/*`

## 6. Service and Responsibility Design

### 6.1 Accounts Services

Account services encapsulate:

- company email validation rules
- pending-signup creation
- OTP issuance and consumption
- user email verification completion
- initial profile creation
- initial subscription trial creation
- student account deactivation and reactivation logic

### 6.2 Search Services

Search services encapsulate:

- text and structured filtering
- heuristic recommendation scoring
- visibility rules by requester role
- directory statistics aggregation

The recommendation engine is rules-based, not ML-based.

### 6.3 Chat Services

Chat services encapsulate:

- authorized conversation retrieval
- message creation
- unread-count computation
- read-state updates
- websocket broadcasts

### 6.4 Payment Services

Payment services encapsulate:

- gateway lookup and abstraction
- pending transaction creation
- hosted checkout payload generation
- signature verification
- webhook normalization
- transaction synchronization
- subscription activation

## 7. API Design

### 7.1 Pattern

- RESTful route grouping by domain
- DRF generic views where possible
- serializer-driven validation and shaping
- role permissions applied at view level

### 7.2 Authentication

- JWT bearer tokens for protected REST APIs
- custom JWT auth integration for DRF
- websocket auth scoped to authenticated conversation participants

### 7.3 Pagination and Filtering

- standard paginated list responses
- default page size of 12
- DRF search and ordering backends where appropriate

## 8. Event and Workflow Design

## 8.1 Registration Event Flow

- registration writes `PendingSignup`
- OTP issuance writes `EmailOTP`
- verification creates the user if needed
- role-specific profile is provisioned
- email-verified notification is created
- audit event is recorded

## 8.2 Verification Flow

- corper submits NIN, call-up, or profile review attempt
- verification attempt is stored
- student verification status fields are synchronized
- admin approves or rejects
- notification and audit events are emitted

## 8.3 Interest Flow

- corper or company creates or updates an `Interest`
- timestamps distinguish who initiated intent
- company notifications are created for new corper interest
- the same interest record can later link into a conversation

## 8.4 Chat Flow

- company initiates or reuses a `Conversation`
- optional interest linkage is attached if present
- messages are stored as `Message`
- channel-layer broadcast delivers realtime updates
- unread/read transitions are persisted

## 8.5 Billing Flow

- frontend requests plan purchase
- backend creates `UserSubscription` in pending state
- backend creates `PaymentTransaction`
- gateway returns checkout data
- polling or webhook confirms status
- successful payment activates the subscription

## 9. Background Jobs

Current background-job usage is intentionally narrow:

- OTP email dispatch can be offloaded to Celery when enabled

The architecture supports expansion to:

- reminder emails
- lifecycle notifications
- scheduled billing or verification housekeeping

## 10. Caching Strategy

- Redis is configured as the default cache backend
- practical current Redis use is dominated by Channels and Celery transport
- there is minimal explicit application-level read caching in the current codebase

Implication:

- database indexing matters more than cache-hit optimization for present search and profile workloads

## 11. Search Strategy

Search is implemented directly on relational querysets with deterministic filters.

Recommendation scoring uses weighted heuristics across:

- qualification
- posting/company location
- age range
- field of study
- skills
- experience descriptors

The system returns recommendation metadata only for the viewer roles allowed to see it.

## 12. Notification Service Design

Notifications are first-class persisted records, not purely ephemeral events.

Benefits:

- UI can display history, unread counts, and read-state transitions
- notifications remain recoverable across frontend refreshes
- audit-sensitive flows are easier to trace

## 13. Payment Integration Design

The payment subsystem uses a gateway abstraction:

- `PaymentGateway` interface
- concrete gateway handlers for Flutterwave and Card
- transaction records decoupled from provider payload structure

This allows:

- multiple providers without rewriting business logic
- uniform subscription activation behavior
- webhook persistence independent of provider

## 14. Security Architecture in Code

- role-specific permissions are explicit and simple
- sensitive identifiers are encrypted and hashed
- signup flow separates unverified pending users from verified accounts
- webhook processing validates signatures where secrets are configured
- audit events are recorded through shared services

## 15. Known Architectural Constraints

- some company-billing logic remains in shared subscription/payment code even though company dashboard billing is no longer part of the active UX
- current Celery usage is lighter than the infrastructure footprint suggests
- production config still requires tightening for hosts, CORS, and secret management

## 16. Architectural Strengths

- domain boundaries are easy to follow
- shared services centralize cross-cutting rules
- auditability is built into major flows
- payment provider abstraction reduces coupling
- realtime chat is integrated without splitting the system into extra services

## 17. Summary

Internally, Corpershub is a clean modular monolith with clear business domains, serializer-centric validation, service-layer business rules, and durable workflow records for verification, interests, chat, audit, and payments. It is well structured for continued product iteration without needing an early microservices split.
