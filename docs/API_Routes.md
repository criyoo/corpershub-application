# API Routes

Base URL: `/api`

This document reflects the current Corpershub route surface in the repo.

## Authentication

- `POST /auth/register/`
- `POST /auth/verify-email/`
- `POST /auth/resend-otp/`
- `POST /auth/login/`
- `POST /auth/logout/`
- `POST /auth/token/refresh/`
- `POST /auth/forgot-password/`
- `POST /auth/reset-password/`
- `POST /auth/reactivation/resolve/`
- `GET /auth/me/`
- `GET /auth/settings/`
- `POST /auth/settings/change-password/`
- `POST /auth/settings/change-email/`
- `POST /auth/settings/change-mobile-number/`
- `POST /auth/settings/delete-account/`

## Company Profile and Admin

- `GET,PATCH /companies/me/`
- `GET /companies/directory/<id>/`
- `GET /companies/admin/`
- `GET,PATCH /companies/admin/<id>/`

## Corper Profile and Admin

- `GET,PATCH /students/me/`
- `GET /students/directory/<id>/`
- `GET /students/admin/`
- `GET /students/admin/verifications/`
- `GET,PATCH /students/admin/verifications/<id>/`
- `GET,PATCH /students/admin/<id>/`

## Search

- `GET /search/students/`
- `GET /search/companies/`

## Interests

- `POST /interests/companies/<company_id>/express/`
- `POST /interests/students/<student_id>/express/`
- `GET /interests/mine/`
- `GET /interests/companies/received/`
- `GET /interests/saved/`
- `GET /interests/received/`

## Chat

- `GET /chat/conversations/`
- `GET /chat/conversations/<conversation_id>/`
- `POST /chat/conversations/initiate/`
- `GET,POST /chat/conversations/<conversation_id>/messages/`
- `WS /ws/chat/<conversation_id>/?token=<jwt>`

## Notifications

- `GET /notifications/`
- `GET /notifications/unread-count/`
- `POST /notifications/<id>/read/`

## Verification

- `GET,POST /verification/attempts/`
- `POST /verification/attempts/<id>/review/`

## Subscriptions and Payments

- `GET,POST /subscriptions/plans/`
- `GET,PATCH /subscriptions/plans/<id>/`
- `GET /subscriptions/me/`
- `POST /payments/transactions/initiate/`
- `POST /payments/transactions/reactivation/initiate/`
- `GET /payments/transactions/status/?reference=<payment_reference>`
- `GET /payments/transactions/<id>/`
- `GET /payments/admin/transactions/`
- `POST /payments/webhooks/<gateway>/`

## Admin Panel

- `GET /adminpanel/overview/`
- `GET /adminpanel/users/`
- `GET,PATCH /adminpanel/users/<id>/`
- `GET,POST /adminpanel/domain-rules/`
- `GET,PATCH /adminpanel/domain-rules/<id>/`
- `GET,POST /adminpanel/options/`
- `GET,PATCH /adminpanel/options/<id>/`
- `GET /adminpanel/audit/`

## API Docs and Media Helpers

- `GET /schema/`
- `GET /docs/swagger/`
- `GET /docs/redoc/`
- `GET /home-backgrounds/`
- `GET /home-backgrounds/<name>`
