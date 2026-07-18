# Functional Requirements Document

## 1. Purpose

This document breaks Corpershub into feature-level behavior and expected outcomes. Corpershub is a two-sided NYSC marketplace, so the functional modules below are tailored to company-corper matching rather than generic e-commerce.

## 2. Functional Modules

## 2.1 User Registration and Login

### Description

Supports account creation, email verification, login, token refresh, logout, password reset, and authenticated account settings.

### Requirements

- Users shall select a role during registration.
- Company registration shall require company name and pass company email-domain validation.
- Registration shall create a pending-signup state before final account creation.
- OTP shall be issued for sign-up verification.
- Email verification shall finalize user creation and initialize the role-specific profile.
- Login shall return JWT access and refresh tokens plus current user metadata.
- Password reset shall use OTP validation.
- Student login shall trigger reactivation guidance if the account has auto-expired after 13 months.

### Acceptance Notes

- Unverified accounts cannot sign in.
- Existing verified emails cannot be reused.

## 2.2 Company Onboarding and Profile Management

### Description

Lets companies create and maintain a structured organization profile and preference set for candidate matching.

### Requirements

- The company profile shall include company identity, location, address, sector, function, company image, and desired corper attributes.
- The system shall expose company profile retrieval and partial update.
- The company profile shall track completeness and verification status.
- Once verified, only designated preference fields and the company image shall remain editable in standard mode.

### Key Fields

- company name
- image
- state and city
- address
- sector and function
- desired qualification
- desired age range
- desired field of study
- desired skills
- desired experience
- contact phone

## 2.3 Corper Onboarding, Verification, and Profile Management

### Description

Lets corpers verify identity-related information, build a marketplace profile, and maintain profile content under role-specific restrictions.

### Requirements

- The corper shall have a profile record initialized at account creation.
- Verification submissions shall support NIN, NYSC call-up number, and profile review.
- Sensitive submissions shall be masked for review and hashed for duplicate detection.
- NIN shall be encrypted at rest.
- The profile shall expose email, biodata, education, gender, posting state, skill, bio, and media.
- Once the profile is fully verified and complete, only selected fields remain editable through the student profile page.
- The admin interface shall expose corper profile data and editable NYSC service year derived from the call-up number.

## 2.4 Search, Filtering, and Discovery

### Description

Supports the marketplace discovery experience for both roles.

### Requirements

- Companies shall search corpers by keyword and structured filters.
- Students shall search companies by keyword and structured filters.
- Search responses shall be paginated.
- Search responses shall include directory statistics.
- Search responses shall include recommendation metadata only when the requesting role is allowed to see it.
- Company search detail pages shall return company profile data relevant to corpers.
- Corper search detail pages shall return company-visible corper detail including email, gender, mobile number, and NYSC service year.

### Recommendation Behavior

The heuristic recommendation engine shall score matches using a combination of:

- qualification fit
- location fit
- age-range fit
- field-of-study fit
- skill fit
- experience-text similarity

## 2.5 Interests

### Description

Captures marketplace intent before or alongside chat.

### Requirements

- A student shall be able to express interest in a company.
- A company shall be able to save or express interest in a corper.
- Interest records shall keep independent student and company timestamps.
- Student interest shall generate a company notification.
- Company users shall have separate views for:
  - corpers who expressed interest in the company
  - corpers the company saved into Interest
- Student users shall have separate views for:
  - companies the student expressed interest in
  - companies that expressed interest in the student

## 2.6 Chat and Messaging

### Description

Supports direct communication between companies and corpers.

### Requirements

- A company shall be able to initiate a conversation with a corper directly.
- The system shall create at most one conversation per company-corper pair.
- If an interest already exists between the pair, the conversation may attach to that interest record.
- A conversation shall expose counterpart identity data appropriate to the current user.
- A participant shall be able to retrieve the conversation list and detail.
- A participant shall be able to post messages to a conversation.
- The system shall broadcast new messages and typing events through WebSockets.
- The system shall mark unread messages as read when appropriate.

### Recent Product Rule

- Companies can communicate with corpers at any time.
- Prior corper interest is not required for conversation initiation.

## 2.7 Notifications

### Description

Supports in-app awareness of important user events.

### Requirements

- Notifications shall be stored persistently.
- Notifications shall support listing and unread count retrieval.
- Notifications shall support mark-as-read actions.
- The system shall create notifications for:
  - successful email verification
  - profile verification updates
  - corper interest received
  - new chat messages
  - payment outcomes where applicable

## 2.8 Subscription, Billing, and Reactivation

### Description

Supports paid access and student reactivation.

### Requirements

- The system shall expose active subscription plans filtered by role when appropriate.
- The system shall list a user’s subscription records.
- The system shall initialize payment transactions and pending subscriptions.
- The system shall confirm payment state through hosted-checkout return and polling.
- The system shall process payment webhooks and activate subscriptions on success.
- Student reactivation shall use a signed token and paid flow after automatic expiry.

### Current Scope Note

- The active frontend billing journey is student-facing.
- Company dashboard billing has been removed from the active company UX.

## 2.9 Payment Processing

### Description

Provides payment gateway abstraction and transaction handling.

### Requirements

- The backend shall support gateway abstraction for Flutterwave and a card stub.
- The current UI shall initiate checkout through Flutterwave.
- Payment records shall track reference, idempotency key, amount, status, and provider payload.
- Webhook events shall be stored for traceability.

## 2.10 Admin Panel

### Description

Provides internal governance tools.

### Requirements

- Admin shall have overview metrics for users, companies, corpers, interests, conversations, and successful payments.
- Admin shall manage users.
- Admin shall manage company and corper records.
- Admin shall review verification attempts and update approval status.
- Admin shall manage email-domain rules.
- Admin shall manage platform options such as sectors, universities, degrees, and posting locations.
- Admin shall review payments and subscriptions.
- Admin shall review audit logs.

## 2.11 Analytics and Reporting

### Description

Current analytics are operational rather than advanced BI.

### Requirements

- The admin overview shall provide headline marketplace counts.
- Directory APIs shall provide online, active, and total population counts for role discovery pages.
- Audit logs shall provide event-level reporting for operational review.

## 3. Explicitly Not Implemented

The following generic cloud-marketplace functions are not part of Corpershub’s current domain model:

- cart and checkout for goods
- order management
- shipping and delivery tracking
- reviews and ratings
- promotions and coupons
- returns and refunds

## 4. Dependencies Between Modules

- Registration depends on OTP issuance and verification.
- Profile onboarding depends on successful account creation.
- Corper full onboarding depends on verification approval.
- Discovery depends on completed records being present in the system.
- Chat depends on authenticated users and conversation authorization.
- Student reactivation depends on the billing and payment modules.

## 5. Summary

Corpershub’s implemented functionality centers on verified onboarding, structured matching, interest tracking, direct chat, admin governance, and student-side billing/reactivation. The platform is a role-based talent marketplace, not a retail commerce workflow.
