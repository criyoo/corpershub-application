# Software Requirements Specification

## 1. Purpose

This SRS defines the functional and non-functional requirements for Corpershub based on the current implementation in the repository and the current product direction.

## 2. System Overview

Corpershub is a web platform that supports three primary roles:

- corpers
- companies
- admins

The platform provides:

- role-based account registration and login
- email verification with OTP
- company profile onboarding
- corper verification and profile onboarding
- privacy-aware marketplace discovery
- interest workflows
- direct chat and realtime messaging
- notifications
- student subscription/reactivation billing
- admin governance and audit visibility

The system is delivered as:

- Next.js frontend
- Django REST API backend
- PostgreSQL database
- Redis for Channels and Celery
- WebSocket support via Django Channels
- optional S3-compatible object storage

## 3. User Roles

### 3.1 Corper

The corper can:

- register and verify email
- complete verification submissions
- complete and maintain a profile
- search companies
- express interest in companies
- view companies that have expressed interest
- chat with companies once a conversation exists
- manage account settings
- access billing and reactivation flows

### 3.2 Company

The company can:

- register with validated email-domain rules
- verify email
- complete and maintain a company profile
- search corpers
- save corpers into Interest
- receive corper interest notifications
- initiate chat with a corper directly
- manage account settings

### 3.3 Admin

The admin can:

- access overview metrics
- manage users
- manage company and corper records
- manage verification outcomes
- inspect subscriptions and payments
- manage email-domain rules
- manage platform options
- inspect audit logs

## 4. Functional Requirements

### 4.1 Authentication and Account Lifecycle

- The system shall allow registration with email, password, and role.
- The system shall require company email-domain validation during company registration.
- The system shall issue OTP codes for sign-up verification.
- The system shall support OTP resend with throttling.
- The system shall issue JWT access and refresh tokens at login.
- The system shall block login for unverified accounts.
- The system shall support forgot-password and reset-password workflows using OTP.
- The system shall support authenticated account settings operations for password, email, mobile number, and account deletion.
- The system shall auto-deactivate student accounts after the configured 13-month lifecycle window.
- The system shall support paid student reactivation through a signed reactivation token workflow.

### 4.2 Company Profile

- The system shall create a company profile at onboarding completion.
- The system shall allow company profile retrieval and update.
- The system shall require a complete set of company fields before a profile can be considered complete.
- The system shall restrict edits to a smaller allowed field set after company verification unless explicit edit mode is used.

### 4.3 Corper Profile and Verification

- The system shall create a corper profile at onboarding completion.
- The system shall allow NIN and NYSC call-up submission through the verification flow.
- The system shall reject duplicate NIN and duplicate call-up submissions.
- The system shall encrypt NIN at rest and hash sensitive identifiers for duplicate detection.
- The system shall allow only limited field updates after the corper profile is locked.
- The system shall compute profile completeness and onboarding completion status.

### 4.4 Discovery and Search

- The system shall provide searchable student and company directories.
- The system shall allow keyword and attribute filtering.
- The system shall return recommendation metadata where permitted by role.
- The system shall expose directory statistics including online, active, and total counts.
- The system shall allow companies to view corper detail pages.
- The system shall allow students to view company detail pages.

### 4.5 Interests

- The system shall allow a student to express interest in a company.
- The system shall allow a company to save or express interest in a student.
- The system shall persist interests as records with timestamps for both sides.
- The system shall expose separate views for sent, received, and saved interests.
- The system shall notify companies when a corper expresses interest.

### 4.6 Chat and Messaging

- The system shall allow companies to initiate conversations with corpers directly.
- The system shall allow reuse of an existing conversation for the same company-corper pair.
- The system shall persist messages and update conversation metadata.
- The system shall support conversation detail and list retrieval.
- The system shall support realtime message and typing delivery over WebSockets.
- The system shall notify recipients of new chat messages.

### 4.7 Notifications

- The system shall store notifications in the database.
- The system shall expose notification listing and unread-count APIs.
- The system shall allow marking notifications as read.

### 4.8 Billing and Payments

- The system shall expose subscription plans.
- The system shall expose the current authenticated user’s subscription history.
- The system shall create payment transactions and pending subscriptions when payment is initiated.
- The system shall support webhook processing and payment status polling.
- The system shall activate paid subscriptions on successful payment.
- The system shall support student account reactivation through billing.

### 4.9 Admin and Audit

- The system shall expose admin-only APIs for overview, users, domain rules, platform options, and audit logs.
- The system shall record audit events for key flows such as auth, verification, interest, chat, payment, and reactivation.

## 5. Non-Functional Requirements

### 5.1 Performance

- Standard list and detail API responses should target sub-2-second p95 response times under expected production load.
- WebSocket connection establishment should target sub-3-second completion for authenticated users.
- Search endpoints should support pagination and predictable latency on indexed fields.

### 5.2 Security

- The system shall require authenticated access by default for protected endpoints.
- The system shall enforce role-based permissions.
- The system shall use JWT bearer authentication for API access.
- The system shall verify webhook signatures when payment secrets are configured.
- The system shall protect sensitive corper identifiers through encryption, masking, and lookup hashing.

### 5.3 Reliability and Availability

- The system should be deployable with separate services for API, workers, Redis, and database.
- The system should tolerate worker restarts without losing persisted state.
- The system should keep audit and payment records durable in PostgreSQL.

### 5.4 Maintainability

- The system shall remain modular by business domain within the Django monolith.
- API schemas shall be available through OpenAPI endpoints.
- Automated tests shall cover critical business workflows.

### 5.5 Usability

- The frontend shall provide role-specific navigation and dashboards.
- The platform shall provide clear onboarding paths for corpers and companies.

## 6. External Integrations

- PostgreSQL for primary persistence
- Redis for Channels and Celery
- SMTP email provider for OTP and password-reset delivery
- Flutterwave payment gateway for the current frontend payment flow
- S3-compatible storage for media in production
- OpenAPI via drf-spectacular

## 7. Assumptions

- users access the system through modern desktop or mobile browsers
- companies are registered with a valid email address and can receive OTP emails
- corpers can provide valid NIN and NYSC call-up details
- media storage and SMTP are correctly configured in each environment
- admins are available to review verification attempts

## 8. Constraints

- The codebase is a modular monolith, not a microservices system.
- The current frontend billing UX is student-facing; company billing infrastructure still exists in backend code but is not part of the active company dashboard flow.
- Celery is present, but current background-job usage is limited primarily to optional async OTP email dispatch.
- Production deployment requires hardening beyond current development defaults.

## 9. Acceptance Criteria

### 9.1 Auth

- A new user can register, receive OTP, verify email, log in, and access the correct role dashboard.

### 9.2 Company

- A company can complete its profile, search corpers, save interest, and start chat from the UI.

### 9.3 Corper

- A corper can submit verification data, complete profile onboarding, browse companies, express interest, and receive company interest.

### 9.4 Chat

- A company can initiate a conversation with a corper even if the corper has not previously expressed interest.

### 9.5 Billing

- A student can view plans, initiate payment, confirm payment status, and use the reactivation flow where applicable.

### 9.6 Admin

- An admin can access overview metrics, review verification attempts, and inspect audit records.
