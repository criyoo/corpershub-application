# Product Vision / Business Requirements Document

## 1. Document Context

- Product: Corpershub
- Product type: two-sided NYSC placement marketplace
- Source of truth: current Corpershub codebase as of March 24, 2026
- Core stack context: Next.js frontend, Django/DRF backend, PostgreSQL, Redis, Channels, Celery, S3-compatible media storage

## 2. Product Vision

Corpershub is a privacy-aware marketplace that connects NYSC corps members looking for PPA and service opportunities with companies searching for qualified corpers. The platform is designed to reduce informal, opaque, and low-trust matching by giving both sides structured profiles, verified onboarding, searchable discovery, interest tracking, realtime chat, and admin oversight.

The product vision is to become the trusted digital marketplace for NYSC placement discovery in Nigeria by combining:

- verified identity and document workflows for corpers
- structured requirement matching for companies
- safe discovery that limits exposure of sensitive information
- faster communication once a match is promising
- administrative controls for platform quality, fraud reduction, and operational governance

## 3. What the Marketplace Is

Corpershub is not a generic e-commerce platform. It is a role-based matching marketplace with these primary capabilities:

- company and corper account creation with email verification
- structured profile onboarding for each side
- corper document verification for NIN and NYSC call-up number
- searchable discovery directories for companies and corpers
- mutual and one-sided interest tracking
- direct company-to-corper chat initiation
- realtime messaging and notifications
- admin management for users, profiles, verification, audit, and platform configuration
- subscription and payment infrastructure, with active student-facing billing and reactivation support

## 4. Target Users

### 4.1 Primary Users

- Corper:
  NYSC corps members who want to discover verified company opportunities, present their academic and service details, indicate interest in companies, receive company interest, and chat with potential placements.

- Company:
  Employers, organizations, and institutions looking to discover qualified corpers by location, field of study, qualification, skill, and related criteria, save prospects, and initiate conversations.

### 4.2 Internal Users

- Admin:
  Internal operators responsible for governance, user oversight, verification review, domain-rule management, payment visibility, audit review, and platform configuration.

## 5. Problems the Product Solves

### 5.1 For Corpers

- difficulty finding relevant companies or placement opportunities
- low transparency in how companies evaluate potential candidates
- lack of trusted digital presence for verified profile discovery
- exposure risk around sensitive identity and service data
- fragmented communication across informal channels

### 5.2 For Companies

- inefficient sourcing of suitable corpers
- poor signal quality in informal sourcing channels
- slow matching and follow-up
- limited structured candidate filtering
- lack of consistent platform records for interest and communication history

### 5.3 For Platform Operations

- need for fraud control and data-governance around sensitive corper records
- need for admin visibility into verification, payment, and user activity
- need for configurable business rules such as company email domain restrictions

## 6. Business Goals

### 6.1 Marketplace Goals

- grow a verified supply of active corper profiles
- attract a high-quality set of legitimate companies
- increase successful introductions and conversations between both sides
- reduce manual matching and support overhead
- establish Corpershub as a trusted marketplace for NYSC placement discovery

### 6.2 Operational Goals

- maintain admin control over verification and moderation workflows
- preserve privacy for sensitive student identifiers and company contact details
- support auditability for critical actions such as sign-up, verification, interest, chat, payment, and account lifecycle changes

### 6.3 Commercial Goals

- monetize access and reactivation where applicable
- retain flexibility to evolve pricing rules without rewriting core marketplace workflows

## 7. Current Revenue Model

The codebase currently contains a full subscription and payment domain with plans, user subscriptions, transactions, webhook processing, and billing screens.

Current effective product position after recent repo updates:

- company-facing billing has been removed from the company dashboard UX
- companies can browse corpers and initiate chat without prior corper interest
- student-facing billing remains active in the frontend and backend
- student account reactivation after automatic 13-month expiry is explicitly billing-driven

Business interpretation:

- active monetization is centered on corper subscription/reactivation flows
- company payment support still exists in the shared billing backend, but it is not part of the current company dashboard journey and should be treated as dormant or transitional unless product policy changes again

## 8. Payment Model

### 8.1 Implemented Payment Capabilities

- subscription plans with pricing and billing interval metadata
- transaction initiation
- hosted checkout handoff
- payment status polling
- webhook processing
- subscription activation on successful payment
- student reactivation payment flow

### 8.2 Payment Providers

- Flutterwave is the active gateway in the current frontend billing experience
- A card abstraction remains in backend services for gateway extensibility

### 8.3 Product Policy

- corpers may require paid access beyond the initial trial/reactivation window
- companies currently operate without an active dashboard billing journey

## 9. Success Metrics

### 9.1 Acquisition and Activation

- number of verified corper sign-ups
- number of verified company sign-ups
- percentage of registered users who complete profile onboarding
- percentage of corpers who complete NIN and NYSC call-up verification

### 9.2 Marketplace Engagement

- number of directory searches performed
- number of interests expressed by corpers
- number of corpers saved by companies
- number of conversations initiated
- conversation reply rate

### 9.3 Commercial Metrics

- paid student subscriptions activated
- student reactivation conversion rate
- payment success rate by gateway

### 9.4 Operational Metrics

- verification turnaround time
- admin review throughput
- failed or duplicate sensitive-document submissions detected
- support incidents tied to onboarding, billing, or chat

## 10. Scope

### 10.1 In Scope

- account registration, verification, login, and account settings
- company onboarding and company profile management
- corper verification and profile management
- directory search and filtering
- heuristic matching recommendations
- interest workflows for both sides
- direct company-to-corper chat
- realtime messaging and notifications
- admin panel and audit visibility
- student billing, subscription, and reactivation flows

### 10.2 Out of Scope

- applicant tracking workflows beyond chat and interest
- external job-board publishing
- interviews, offer management, and placement contracting
- ratings, reviews, coupons, shipping, cart, and order fulfillment
- advanced BI dashboards beyond the current admin overview counts

## 11. Scope Priorities

### P0

- trustworthy onboarding and login
- verified corper profiles
- company profile completion
- discovery and search
- interests
- direct chat
- admin verification and oversight

### P1

- subscription monetization and reactivation
- richer recommendation ranking
- more detailed analytics and reporting
- cloud-ready deployment hardening

### P2

- broader payments strategy
- automation around lifecycle reminders and billing events
- deeper operational tooling

## 12. Admin Role Requirements

Admins must be able to:

- view overall platform counts
- manage users and activation state
- manage company and corper records
- review verification attempts and update statuses
- review payment transactions and subscriptions
- manage company email-domain rules
- manage configurable platform options
- inspect audit logs for sensitive actions

## 13. Business Risks and Notes

- the repo still contains some company subscription artifacts in shared billing code and admin views, even though company dashboard billing has been removed
- production security hardening is still required for deployment-grade configuration
- the marketplace depends heavily on verification quality and moderation discipline for trust

## 14. Summary

Corpershub is a verified, privacy-aware matching marketplace for NYSC corps members and companies. Its current business shape is a free-to-company discovery and communication experience paired with active student-side billing and reactivation support, all backed by admin controls, auditability, and extensible payment infrastructure.
