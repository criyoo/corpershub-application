# Corpershub User Acceptance Testing Guide

## Purpose

This guide helps testers validate Corpershub from a real user perspective. It focuses on the main journeys for the three active roles in the product:

- Corper
- Company
- Admin

The goal of UAT is to confirm that a tester can complete key business tasks successfully through the UI, not just that APIs respond.

## Scope

This guide covers:

- registration, email verification, login, and password reset
- corper verification and profile completion
- company profile completion
- company and corper discovery
- interest workflows
- chat and notifications
- account settings
- corper billing visibility
- core admin review flows

This guide does not cover:

- Terraform or infrastructure validation
- backend API-only testing
- load, security, or penetration testing
- deep browser compatibility certification

## Recommended Test Environment

Use a deployed dev/UAT environment when available. For local testing, the repository already includes demo credentials and seed data.

Recommended setup:

- Frontend available and reachable in a browser
- Backend API available
- Email/OTP delivery configured, or testers have a safe way to access OTP values in the target environment
- Seed data loaded if testing locally
- A clean browser session or incognito window for each role

## Demo Accounts

The repository README and seed command define these demo users:

| Role | Email | Password | Notes |
| --- | --- | --- | --- |
| Admin | `admin@Corpershub.ng` | `AdminPass123!` | Use for verification review and platform checks |
| Company | `talent@brightfuture.ng` | `CompanyPass123!` | Seeded as verified and profile-complete |
| Corper | `corper1@demo.ng` | `CorperPass123!` | Seeded profile for discovery and interest testing |
| Corper | `corper2@demo.ng` | `CorperPass123!` | Second seeded corper profile |

Seeded sample records include:

- Company: `Bright Future Logistics`
- Corpers: `Adaeze Okafor`, `Musa Ibrahim`
- Existing interest records from seeded corpers to the seeded company

## Test Data Guidance

Use seeded accounts for smoke tests and realistic discovery/chat flows. Use fresh accounts when you want to validate registration, OTP, first-time onboarding, or rejection/approval workflows end to end.

For new account creation:

- Corper signup can use a normal email address
- Company signup should use a work email with a non-free domain in production-like environments
- In local/dev, `gmail.com` is temporarily allowed for company signup for testing

Suggested fresh test accounts:

- `uat.corper.<date>@example.com`
- `uat.company.<date>@example.com`

## How To Record UAT Results

For each test case, record:

- `Pass` or `Fail`
- actual result
- screenshot or short screen recording for failures
- browser and environment used
- defect reference if a bug is logged

## Exit Criteria

UAT can be considered successful when:

- all critical user journeys pass
- no blocker or critical severity defects remain open
- any medium/low defects are accepted or scheduled

## Test Cases

### 1. Public Entry And Authentication

| ID | Scenario | Steps | Expected Result |
| --- | --- | --- | --- |
| AUTH-01 | Open landing and public navigation | Open the homepage. Navigate to `Register`, `Login`, `Corpers`, and `Companies` if visible. | Main entry pages load without error and navigation works. |
| AUTH-02 | Corper registration | Go to `Register` > `Corper`. Enter a new email and password. Submit. | Registration succeeds and the app routes to email verification with a success message that an OTP was sent. |
| AUTH-03 | Company registration | Go to `Register` > `Company`. Enter a valid company email and password. Submit. | Registration succeeds for allowed company emails. Free-email company signup should be blocked in production-like environments unless explicitly allowed. |
| AUTH-04 | Email verification | From the verification page, enter the correct email and OTP. Submit. | Email is verified successfully and the user is redirected to sign in. |
| AUTH-05 | Resend OTP | On the verification page, click `Resend OTP`. | A new OTP can be requested and a confirmation message is shown. |
| AUTH-06 | Login | Sign in with a verified account. | Login succeeds and the user lands on the correct dashboard for their role. |
| AUTH-07 | Unverified account cannot log in | Try logging in with a newly registered account before OTP verification. | Login is blocked and the user is informed that verification is required. |
| AUTH-08 | Forgot/reset password | Use `Forgot password`, request a reset code, complete reset, then sign in with the new password. | Password reset works end to end and the old password no longer works. |

### 2. Corper UAT Journey

Use a fresh corper account for onboarding tests and a seeded corper account for discovery/chat tests if needed.

| ID | Scenario | Steps | Expected Result |
| --- | --- | --- | --- |
| CORPER-01 | Corper dashboard access | Sign in as a corper. | Corper navigation shows `Overview`, `Profile`, `Settings`, `Verification`, `Discover Companies`, `My Interests`, `Companies Interested`, `Billing`, and `Chat`. |
| CORPER-02 | Verification center loads | Open `Verification`. | The verification center loads and shows NIN and NYSC call-up status cards. |
| CORPER-03 | Submit NIN | Enter a valid 11-digit NIN and submit. | Submission is accepted and status changes to pending review. |
| CORPER-04 | Submit NYSC call-up number | Enter a valid call-up number and submit. | Submission is accepted and status changes to pending review. |
| CORPER-05 | Invalid verification data blocked | Enter an invalid NIN or malformed call-up number. | The form prevents submission and shows a validation error. |
| CORPER-06 | Admin approval unlocks next step | After admin approval of both verification items, refresh the corper view. | The page reflects verified document status and directs the user to complete the profile. |
| CORPER-07 | Profile cannot be fully completed before document approval | Open `Profile` before both verification items are approved. | The user is told to complete NIN and NYSC verification before full profile editing. |
| CORPER-08 | Complete corper profile | Fill in full name, date of birth, gender, posting state, field of study, degree, university, graduation year, mobile number, primary skill, bio, and upload a photo. Save. | Profile saves successfully and completeness indicators show the profile is complete. |
| CORPER-09 | Missing profile fields are blocked | Leave one or more required fields empty and try to save. | Save is blocked with a clear message listing missing fields. |
| CORPER-10 | Search companies | Open `Discover Companies`. Search by keyword, state, sector, function, or skill-related terms. | Relevant company cards appear and results refresh correctly. |
| CORPER-11 | Open company detail | From the directory, open a company detail page. | Company details load, including location, sector/function, preferences, summary, and recommendation info where available. |
| CORPER-12 | Express interest in a company | On a company detail page, click `I'm interested`. | Interest is saved successfully and the button changes state to show interest has already been sent. |
| CORPER-13 | View sent interests | Open `My Interests`. | The company appears in the list of companies the corper has expressed interest in. |
| CORPER-14 | View companies that expressed interest | Open `Companies Interested`. | Any companies that saved or expressed interest in the corper appear in the list. |
| CORPER-15 | Chat inbox and thread | Open `Chat`. Open an existing conversation if available. Send a message. | Messages load correctly, the new message appears in the thread, and the conversation remains accessible from the inbox. |
| CORPER-16 | Notifications | Open `Notifications` or the corper interest/notification area provided in the UI. | Interest and chat-related activity is visible when present, and unread/read behavior is sensible. |
| CORPER-17 | Billing page visibility | Open `Billing`. Review available plan information and current subscription/trial status. | The billing page loads and accurately reflects current access state. |
| CORPER-18 | Settings updates | Open `Settings`. Change password, email, mobile number, and open profile edit mode. | Settings changes succeed with the correct confirmation messages. |
| CORPER-19 | Delete account flow | In `Settings`, attempt account deletion using the current password. | Account deletion requires password confirmation and, if confirmed, removes access and returns the user to the public area. |

### 3. Company UAT Journey

Use the seeded company account for discovery and chat tests. Use a fresh company account for registration and first-time profile completion.

| ID | Scenario | Steps | Expected Result |
| --- | --- | --- | --- |
| COMPANY-01 | Company dashboard access | Sign in as a company. | Company navigation shows `Overview`, `Profile`, `Settings`, `Discover Corpers`, `My Interest`, `Corpers Interested`, and `Chat`. |
| COMPANY-02 | Complete company profile | Open `Profile`. Fill in company name, registration number, tax identification number, sector, function, state, city, address, contact phone, company summary, desired qualification, desired age range, desired field of study, desired skills, desired experience, and upload a profile image. Save. | Profile saves successfully and completeness/verification state updates correctly. |
| COMPANY-03 | Invalid registration or tax number blocked | Enter an invalid company registration number or tax identification number. | Save is blocked with a clear validation message. |
| COMPANY-04 | Missing profile fields are blocked | Leave required company profile fields blank and try to save. | Save is blocked with a message listing missing fields. |
| COMPANY-05 | Verified profile edit restrictions | Use a verified company profile and attempt editing in normal mode versus edit mode. | The product respects the current rule that verified profiles have limited edits unless edit mode is enabled. |
| COMPANY-06 | Search corpers | Open `Discover Corpers`. Search by posting state, course, graduation year, skill, gender, or keyword. | Relevant corper cards appear and search results refresh correctly. |
| COMPANY-07 | Open corper detail | From the directory, open a corper detail page. | The company can see the corper's visible details, including qualification, location, skills, bio, email, mobile number, and NYSC service year when available. |
| COMPANY-08 | Save interest in a corper | On a corper detail page, click `Interested`. | The interest is saved and the button state updates to prevent duplicate submission. |
| COMPANY-09 | Start chat directly | On a corper detail page, click `Chat` even if the corper has not first expressed interest. | A conversation opens successfully because direct initiation is allowed for companies. |
| COMPANY-10 | View saved interest list | Open `My Interest`. | Saved corpers appear with the correct profile information and can be opened or chatted with. |
| COMPANY-11 | View corpers who expressed interest | Open `Corpers Interested`. | Corpers who showed interest in the company appear in the list and can be opened or messaged. |
| COMPANY-12 | Chat inbox and thread | Open `Chat`. Open an existing conversation and send a message. | The conversation thread loads, messages can be sent, and the conversation stays accessible from the inbox. |
| COMPANY-13 | Settings updates | Open `Settings`. Update password, email, mobile/contact number, and open profile edit mode. | Changes save successfully and updated values are reflected in the account. |

### 4. Admin UAT Journey

Use the seeded admin account for these tests.

| ID | Scenario | Steps | Expected Result |
| --- | --- | --- | --- |
| ADMIN-01 | Admin login and navigation | Sign in as admin. | Admin lands on the admin workspace and sees navigation for overview, users, companies, corpers, verifications, subscriptions, payments, audit, and configuration. |
| ADMIN-02 | Overview metrics | Open `Overview`. | Headline platform counts load without error. |
| ADMIN-03 | Users list | Open `Users`. Search or browse. | User records load and are attributable to the correct roles. |
| ADMIN-04 | Company records | Open `Companies`. | Company records load and verification status is visible. |
| ADMIN-05 | Corper profiles | Open `Profiles` or `Corpers`. | Corper records load and show the expected profile data. |
| ADMIN-06 | Verification attempts review | Open `Verification Attempts`. Review a submitted NIN or call-up attempt. Approve or reject it. | Status updates persist successfully and the action is reflected when the corper refreshes their verification page. |
| ADMIN-07 | Corper verification summary | Open `Corper Verifications`. Update corper verification fields where needed. | Updated statuses persist and remain consistent with the corper-facing experience. |
| ADMIN-08 | Configuration and domain rules | Open `Configuration`. Review domain rules and platform options. Add or update a safe test rule if the environment permits. | Configuration pages load and valid changes save correctly. |
| ADMIN-09 | Payments and subscriptions | Open `Payments` and `Subscriptions`. | Billing records and plans load without error when data exists. |
| ADMIN-10 | Audit log | Open `Audit`. | Audit events are visible and recent actions appear where expected. |

### 5. Cross-Role End-To-End Scenarios

These are the most important business-level tests because they validate the marketplace flow across users.

| ID | Scenario | Steps | Expected Result |
| --- | --- | --- | --- |
| E2E-01 | Corper interest reaches company | Corper signs in, opens a company profile, clicks `I'm interested`, then company opens `Corpers Interested`. | The company can see the corper in its interest inbox. |
| E2E-02 | Company saves corper to interest list | Company signs in, opens a corper profile, clicks `Interested`, then opens `My Interest`. | The saved corper appears in the company's interest list. |
| E2E-03 | Company starts chat with corper | Company opens a corper profile and starts a chat. Corper opens `Chat`. | Both users can access the same conversation and exchange messages. |
| E2E-04 | Admin approval changes corper experience | Corper submits NIN and call-up details, admin approves both, corper refreshes `Verification` and `Profile`. | The corper sees approved status and can proceed with full profile completion. |
| E2E-05 | Search reflects profile data | Update company or corper profile attributes, then search from the opposite role. | Discovery results reflect the updated searchable fields after refresh. |

## Suggested Execution Order

Run UAT in this order to reduce blockers:

1. Authentication smoke tests
2. Admin login sanity check
3. Fresh corper onboarding and verification submission
4. Admin approval of corper documents
5. Corper profile completion and company discovery
6. Fresh or seeded company profile validation and corper discovery
7. Interest and chat end-to-end flows
8. Settings and billing checks
9. Admin reporting, audit, and configuration review

## Known Product Notes For Testers

- Company billing is not part of the active company frontend flow, so do not treat the absence of a company billing journey as a defect unless the test scope explicitly includes dormant functionality.
- Corper billing is active in the frontend.
- Company users can initiate chat directly with corpers; prior corper interest is not required.
- Some discovery and interest results may already exist when seed data has been loaded.
- If repeated testing causes polluted state, use fresh accounts or reset the environment before rerunning UAT.

## Defect Logging Template

Use this simple format when reporting issues:

- Test Case ID:
- Title:
- Environment:
- User Role:
- Preconditions:
- Steps to Reproduce:
- Expected Result:
- Actual Result:
- Severity:
- Screenshot/Recording:

## Sign-Off

Record final UAT sign-off with:

- date tested
- environment tested
- tester name
- business/product approver
- overall outcome: `Pass`, `Pass with conditions`, or `Fail`
