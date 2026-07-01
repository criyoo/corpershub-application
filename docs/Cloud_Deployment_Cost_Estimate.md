# Corpershub Cloud Deployment Cost Estimate

Reviewed on: 2026-03-23

## Scope

This document estimates monthly cost for the infrastructure and software needed to run Corpershub in:

- a scheduled development/sandbox environment
- a lean production launch environment for about 10,000 users
- a growth production environment sized toward about 200,000 users

These are planning estimates, not invoices. They are intended to help choose the platform shape before implementation.

## Key Assumptions

- Primary cloud: AWS
- Region: `eu-west-1`
- ECS runtime: AWS Fargate on ARM/Graviton
- Development runs on a schedule of `6 hours/day for 22 days`, or `132 hours/month`
- Production launch uses single-AZ RDS and single-node Valkey to reduce early spend
- Production growth keeps RDS in Single-AZ and uses replicated Valkey
- CloudFront viewer pricing uses the South Africa viewer tier as a conservative proxy for Nigeria because AWS does not publish a Nigeria-specific viewer tier in the pricing source reviewed
- GitHub Team assumes 5 paid users
- GitHub Actions usage remains inside the included monthly minutes
- OpenAI costs are optional and not included in the core totals because the current codebase does not yet contain an AI feature
- The development ElastiCache node is still budgeted for the full month because managed Valkey does not provide the same simple stop/start savings as ECS tasks and a stopped RDS instance

## Unit Prices Used

| Component | Unit price used | Notes |
| --- | ---: | --- |
| AWS Fargate ARM vCPU | $0.03238 per vCPU-hour | `eu-west-1` |
| AWS Fargate ARM memory | $0.00356 per GB-hour | `eu-west-1` |
| ALB hourly | $0.0252 per hour | `eu-west-1` |
| ALB LCU | $0.008 per LCU-hour | `eu-west-1` |
| RDS PostgreSQL `db.t4g.micro` Single-AZ | $0.017 per hour | `eu-west-1` |
| RDS PostgreSQL `db.t4g.medium` Single-AZ | $0.069 per hour | `eu-west-1` |
| RDS PostgreSQL `db.t4g.large` Single-AZ | $0.138 per hour | `eu-west-1` |
| RDS gp3 storage Single-AZ | $0.127 per GB-month | `eu-west-1` |
| ElastiCache for Valkey `cache.t4g.micro` | $0.0136 per node-hour | `eu-west-1` |
| ElastiCache for Valkey `cache.t4g.small` | $0.0272 per node-hour | `eu-west-1` |
| ElastiCache for Valkey `cache.t4g.medium` | $0.0544 per node-hour | `eu-west-1` |
| S3 Standard storage | $0.023 per GB-month | `eu-west-1` |
| S3 PUT/COPY/POST/LIST | $0.005 per 1,000 requests | `eu-west-1` |
| S3 GET and other | $0.004 per 10,000 requests | `eu-west-1` |
| CloudFront data transfer out | $0.11 per GB for first 10 TB | South Africa viewer tier used conservatively |
| CloudFront HTTPS requests | $0.012 per 10,000 requests | South Africa viewer tier used conservatively |
| Route 53 hosted zone | $0.50 per hosted zone-month | two public zones assumed |
| SES outbound email | $0.10 per 1,000 emails | attachments excluded |
| SSM Parameter Store standard tier | No additional charge | assumes standard parameters and standard throughput |
| SSM Parameter Store advanced tier | $0.05 per advanced parameter-month | only if advanced parameters are needed |
| SSM Parameter Store advanced or higher-throughput API interactions | $0.05 per 10,000 API interactions | only if advanced parameters or higher throughput are enabled |
| AWS WAF | $5 per Web ACL + $1 per rule + $0.60 per 1M requests | custom-rule estimate |
| ECR private registry storage | $0.10 per GB-month | estimated small image footprint |
| CloudWatch logs | approx. $0.50 per GB ingested | custom metrics and alarms added as budget lines |
| GitHub Team | $4 per user-month | 5 users assumed |
| GitHub Actions included minutes | 3,000 minutes per month | GitHub Team included usage |
| GitHub Actions Linux overage | $0.006 per minute | only if included minutes are exceeded |
| OpenAI GPT-5.4 | $2.50 / 1M input, $15 / 1M output | optional |
| OpenAI GPT-5.4 mini | $0.75 / 1M input, $4.50 / 1M output | optional |
| OpenAI GPT-5.4 nano | $0.20 / 1M input, $1.25 / 1M output | optional |

## Monthly Estimate By Component

### Shared Across Environments

| Shared component | Monthly estimate | Notes |
| --- | ---: | --- |
| Domain registration | $0.92 | assumes about $11/year with a budget registrar |
| Route 53 hosted zones | $1.00 | `Corpershub.com` and delegated `dev.Corpershub.com` |
| ACM public certificates | $0.00 | no charge for public certs used with integrated AWS services |
| GitHub Team | $20.00 | 5 users |
| GitHub Actions overage | $0.00 | assumes usage stays inside included 3,000 monthly minutes |

Shared monthly subtotal: **$21.92**

### Development / Sandbox

Assumptions:

- API task: 1 x `0.5 vCPU / 1 GB`
- Worker: 1 x `0.25 vCPU / 0.5 GB`
- Beat: 1 x `0.25 vCPU / 0.5 GB`
- ALB active only during `132` scheduled dev hours
- RDS `db.t4g.micro` Single-AZ
- 30 GB database storage
- 1 x `cache.t4g.micro`
- 20 GB object storage
- 20 GB CDN egress

| Component | Monthly estimate |
| --- | ---: |
| ECS Fargate API | $2.61 |
| ECS Fargate worker | $1.30 |
| ECS Fargate beat | $1.30 |
| Application Load Balancer | $3.59 |
| RDS PostgreSQL instance | $2.24 |
| RDS storage | $3.81 |
| ElastiCache for Valkey | $9.93 |
| ECR | $1.00 |
| S3 storage and requests | $0.59 |
| CloudFront CDN | $2.44 |
| SES | $0.50 |
| SSM Parameter Store | $0.00 |
| CloudWatch | $3.00 |

Development runtime subtotal: **$32.31**

Development total including shared monthly costs: **$54.23**

Note: if dev is kept on 24x7 instead of scheduled hours, expect it to move materially above this estimate because ECS, ALB, and the RDS instance would all rise.

### Production Launch Baseline

Assumptions:

- 2 API tasks at `0.5 vCPU / 1 GB`
- 1 worker task at `0.5 vCPU / 1 GB`
- 1 beat task at `0.25 vCPU / 0.5 GB`
- ALB average load about 1 LCU
- RDS `db.t4g.medium` Single-AZ
- 100 GB database storage
- 1 x `cache.t4g.small`
- 100 GB object storage
- 300 GB CDN egress
- 4 million HTTPS CDN requests
- 50,000 outbound emails
- WAF with 8 rules and about 6 million inspected requests

| Component | Monthly estimate |
| --- | ---: |
| ECS Fargate API | $28.84 |
| ECS Fargate worker | $14.42 |
| ECS Fargate beat | $7.21 |
| Application Load Balancer | $24.24 |
| RDS PostgreSQL instance | $50.37 |
| RDS storage | $12.70 |
| ElastiCache for Valkey | $19.86 |
| ECR | $2.00 |
| S3 storage and requests | $4.15 |
| CloudFront CDN | $37.80 |
| SES | $5.00 |
| AWS WAF | $16.60 |
| SSM Parameter Store | $0.00 |
| CloudWatch | $10.00 |

Production launch runtime subtotal: **$233.19**

Production launch total including shared monthly costs: **$255.11**

### Production Growth Baseline

Assumptions:

- 4 API tasks at `1 vCPU / 2 GB`
- 2 worker tasks at `1 vCPU / 2 GB`
- 1 beat task at `0.25 vCPU / 0.5 GB`
- ALB average load about 4 LCUs
- RDS `db.t4g.large` Single-AZ
- 300 GB database storage
- 2 x `cache.t4g.medium` for primary plus replica
- 400 GB object storage
- 2 TB CDN egress
- 25 million HTTPS CDN requests
- 300,000 outbound emails
- WAF with 8 rules and about 40 million inspected requests

| Component | Monthly estimate |
| --- | ---: |
| ECS Fargate API | $115.34 |
| ECS Fargate worker | $57.67 |
| ECS Fargate beat | $7.21 |
| Application Load Balancer | $41.76 |
| RDS PostgreSQL instance | $100.74 |
| RDS storage | $38.10 |
| ElastiCache for Valkey | $79.42 |
| ECR | $3.00 |
| S3 storage and requests | $20.20 |
| CloudFront CDN | $250.00 |
| SES | $30.00 |
| AWS WAF | $37.00 |
| SSM Parameter Store | $0.00 |
| CloudWatch | $25.00 |

Production growth runtime subtotal: **$805.44**

Production growth total including shared monthly costs: **$827.36**

## Cross-Environment Summary Table

| Component | Development | Production (Start-up) | Production (Scaled) |
| --- | ---: | ---: | ---: |
| ECS Fargate API | $2.61 | $28.84 | $115.34 |
| ECS Fargate worker | $1.30 | $14.42 | $57.67 |
| ECS Fargate beat | $1.30 | $7.21 | $7.21 |
| Application Load Balancer | $3.59 | $24.24 | $41.76 |
| RDS PostgreSQL instance | $2.24 | $50.37 | $100.74 |
| RDS storage | $3.81 | $12.70 | $38.10 |
| ElastiCache for Valkey | $9.93 | $19.86 | $79.42 |
| ECR | $1.00 | $2.00 | $3.00 |
| S3 storage and requests | $0.59 | $4.15 | $20.20 |
| CloudFront CDN | $2.44 | $37.80 | $250.00 |
| SES | $0.50 | $5.00 | $30.00 |
| AWS WAF | $0.00 | $16.60 | $37.00 |
| SSM Parameter Store | $0.00 | $0.00 | $0.00 |
| CloudWatch | $3.00 | $10.00 | $25.00 |
| Runtime subtotal | **$32.31** | **$233.19** | **$805.44** |
| Domain registration | $0.92 | $0.92 | $0.92 |
| Route 53 hosted zones | $1.00 | $1.00 | $1.00 |
| ACM public certificates | $0.00 | $0.00 | $0.00 |
| GitHub Team | $20.00 | $20.00 | $20.00 |
| GitHub Actions overage | $0.00 | $0.00 | $0.00 |
| Total including shared monthly costs | **$54.23** | **$255.11** | **$827.36** |

## Optional AI Budget Rows

The current codebase does not show an AI feature today, so these are optional planning rows only.

Example monthly token budget:

- 10 million input tokens
- 2 million output tokens

| Optional AI model | Example monthly estimate | Notes |
| --- | ---: | --- |
| OpenAI GPT-5.4 nano | $4.50 | low-cost classification or triage |
| OpenAI GPT-5.4 mini | $16.50 | best cost/performance balance for app-side agent workflows |
| OpenAI GPT-5.4 | $55.00 | only use for harder reasoning tasks |

Recommendation:

- Use `GPT-5.4 mini` if you add an in-app support or admin assistant.
- Use `GPT-5.4 nano` for lightweight classification, tagging, or queue triage.
- Avoid defaulting to full `GPT-5.4` unless the workflow truly needs it.

## Best Cost Optimizations Without Hurting Performance

### 1. Use ARM/Graviton Everywhere You Can

This estimate already assumes ARM Fargate and Graviton-based database/cache classes.

### 2. Schedule Development Off Outside Working Hours

That is the biggest easy saving in the sandbox account.

### 3. Use ElastiCache For Valkey Instead Of Redis OSS

The current code uses the Redis protocol, so Valkey is a clean cost optimization.

### 4. Consider S3-Compatible Storage For Frontend And Public Media

Because the backend already supports `AWS_S3_ENDPOINT_URL`, moving frontend and public media to Cloudflare R2 is a realistic cost-reduction path.

Estimated replacement cost for the frontend/media storage and CDN layer:

| Alternative edge/storage option | Launch estimate | Growth estimate | Notes |
| --- | ---: | ---: | --- |
| Cloudflare R2 storage + operations | $3.17 | $15.90 | no egress charge assumed |

If you replace the `S3 + CloudFront` rows with the R2 estimate:

- Production launch runtime drops from about **$233.19** to about **$194.41**
- Production growth runtime drops from about **$805.44** to about **$551.14**

This is the single cleanest infrastructure cost lever available if public asset traffic becomes heavy.

## Recommendation Summary

If you want the simplest first production platform:

- Start with the AWS-first launch profile at roughly **$255/month including shared tooling**
- Keep dev scheduled to stay near **$54/month including shared tooling**
- Plan for a growth profile around **$827/month including shared tooling**

If asset bandwidth grows faster than expected:

- keep backend, database, cache, secrets, email, and CI/CD on AWS
- move frontend and public media to an S3-compatible lower-egress option

## Pricing Sources

AWS:

- AWS Fargate pricing: <https://aws.amazon.com/fargate/pricing/>
- AWS public price list JSON for Amazon ECS in `eu-west-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/eu-west-1/index.json>
- AWS public price list JSON for Amazon RDS in `eu-west-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/eu-west-1/index.json>
- AWS public price list JSON for Amazon ElastiCache in `eu-west-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonElastiCache/current/eu-west-1/index.json>
- AWS public price list JSON for Amazon S3 in `eu-west-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/eu-west-1/index.json>
- AWS public price list JSON for Application Load Balancer in `eu-west-1`: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/eu-west-1/index.json>
- AWS public price list JSON for Amazon CloudFront: <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudFront/current/index.json>
- Route 53 pricing: <https://aws.amazon.com/route53/pricing/>
- SES pricing: <https://aws.amazon.com/ses/pricing/>
- AWS WAF pricing: <https://aws.amazon.com/waf/pricing/>
- CloudWatch pricing: <https://aws.amazon.com/cloudwatch/pricing/>
- ACM pricing: <https://aws.amazon.com/certificate-manager/pricing/>
- AWS Systems Manager pricing: <https://aws.amazon.com/systems-manager/pricing/>

GitHub:

- GitHub pricing: <https://github.com/pricing>
- GitHub Actions billing: <https://docs.github.com/en/billing/concepts/product-billing/github-actions>

OpenAI:

- OpenAI API pricing: <https://openai.com/api/pricing/>

Other optional cost-reduction reference:

- Porkbun FAQ on at-cost domain pricing approach: <https://porkbun.com/about/porkbun-faq>
