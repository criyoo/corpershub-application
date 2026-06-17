# Corpershub WordPress / GoDaddy Deployment Assessment

Reviewed on: 2026-03-23

## Executive Summary

The current Corpershub codebase cannot be deployed directly to WordPress hosting on GoDaddy.

Reason:

- The frontend is a Next.js application.
- The backend is a Django ASGI application.
- The backend depends on PostgreSQL, Redis, Celery, WebSockets, and S3-compatible object storage.

That means a WordPress-on-GoDaddy option should be understood in one of these ways:

1. WordPress on GoDaddy for the marketing/public-content site only
2. A hybrid setup where WordPress handles content but the actual application stays on its own platform
3. A full replatform of the product into WordPress/PHP plugins and themes

For this product, option 1 is reasonable, option 2 is possible, and option 3 is technically possible but not recommended.

## Why A Direct WordPress Deployment Does Not Fit This Codebase

The repository currently contains:

- Next.js frontend pages and client-side app flows
- Django REST APIs
- Django Channels WebSockets for chat
- Celery worker and beat processes
- PostgreSQL
- Redis-compatible caching and broker usage
- S3-compatible file storage

The app also includes product behavior that is awkward to reproduce cleanly in standard WordPress hosting:

- multi-role authentication and profile workflows
- privacy-sensitive search and discovery logic
- real-time chat
- payment webhook handling
- background job processing
- admin workflows and verification queues

## Recommended Interpretation Of A WordPress + GoDaddy Option

If you want to use WordPress via GoDaddy, the safest use is:

- `Corpershub.com` marketing pages on GoDaddy Managed WordPress
- the actual application on a separate app platform
- app links from WordPress into the live application

If you want the entire Corpershub product to run on WordPress, that is not a deployment exercise. It is a replatform project.

## Cost Scenarios

### Scenario A: WordPress On GoDaddy For Marketing Site Only

Best use case:

- landing pages
- blog/news
- company info pages
- SEO content
- support content

Suggested GoDaddy plan:

- Managed Hosting for WordPress `Deluxe` or `Ultimate`

Official pricing reviewed:

- GoDaddy Managed WordPress `Basic`: `$6.99/mo` first term, auto-renews at `$14.99/mo`
- GoDaddy Managed WordPress `Deluxe`: `$10.99/mo` first term, auto-renews at `$19.99/mo`
- GoDaddy Managed WordPress `Ultimate`: `$14.99/mo` first term, auto-renews at `$26.99/mo`

GoDaddy also advertises:

- free domain for the first year on annual plans
- free SSL certificate
- daily backups
- WAF
- malware scans and removal

Estimated monthly recurring cost for a marketing-only setup:

| Component | First-term estimate | Renewal estimate | Notes |
| --- | ---: | ---: | --- |
| GoDaddy Managed WordPress Deluxe | $10.99 | $19.99 | best balance for content site |
| Domain | $0.00 to $1.83 | $1.83 | first year may be included; later use about `$21.99/year` |
| Premium theme/plugins | $0 to $20 | $0 to $20 | optional |
| Transactional email/newsletter tools | $0 to $15 | $0 to $15 | optional |

Expected total:

- First term: about **$11 to $48/month**
- Renewal: about **$22 to $57/month**

This is cheap and workable, but it does not replace the Corpershub application platform.

### Scenario B: Hybrid WordPress + Separate App Platform

Best use case:

- WordPress handles public content and SEO
- Corpershub app remains on its own backend/frontend platform

Estimated monthly recurring cost:

| Component | First-term estimate | Renewal estimate | Notes |
| --- | ---: | ---: | --- |
| GoDaddy Managed WordPress Deluxe or Ultimate | $10.99 to $14.99 | $19.99 to $26.99 | marketing layer |
| Current recommended app platform | about $255 | about $255 | from the updated AWS launch estimate document |

Expected total:

- First term: about **$269 to $273/month**
- Renewal: about **$278 to $285/month**

This is the cleanest WordPress-related option if you want WordPress for content without compromising the application architecture.

### Scenario C: Full WordPress Replatform On GoDaddy Managed WordPress

This means rebuilding Corpershub into WordPress plugins/themes and PHP-based workflows.

Important constraint:

GoDaddy Managed WordPress pricing looks cheap, but that pricing is for WordPress hosting, not for replacing a custom Next.js + Django application with feature parity.

Likely recurring components for a serious WordPress rebuild:

- GoDaddy Managed WordPress `Ultimate`
- commercial membership/profile plugins
- workflow/form plugins
- commercial search/filter plugins
- backup and migration tooling
- transactional email
- a chat plugin or external messaging service
- custom plugin maintenance

Estimated monthly recurring cost:

| Component | First-term estimate | Renewal estimate | Notes |
| --- | ---: | ---: | --- |
| GoDaddy Managed WordPress Ultimate | $14.99 | $26.99 | top managed WP tier reviewed |
| Domain | $0.00 to $1.83 | $1.83 | later use domain renewal estimate |
| Commercial plugin stack | $60 to $250 | $60 to $250 | inference; depends on plugin choices |
| Email and misc SaaS | $5 to $30 | $5 to $30 | SMTP, forms, support, etc. |
| External chat/search add-ons | $20 to $120 | $20 to $120 | likely needed for feature parity |

Expected total:

- First term: about **$100 to $417/month**
- Renewal: about **$114 to $429/month**

This still does not remove the main problem: WordPress is a weak fit for the core real-time application requirements.

### Scenario D: Full WordPress Replatform On GoDaddy Self-Managed VPS

This is the more realistic GoDaddy path if you insist on running a custom WordPress-based product with heavier functionality.

Official pricing reviewed:

- GoDaddy self-managed VPS `2 vCPU / 4 GB`: `$17.99/mo` first term
- GoDaddy self-managed VPS `4 vCPU / 8 GB`: `$34.99/mo` first term, auto-renews at about `$49.99/mo`
- GoDaddy self-managed VPS `4 vCPU / 16 GB`: `$44.99/mo` first term, auto-renews at about `$59.99/mo`
- GoDaddy advertises free SSL for the first year, with SSL renewal shown at `$119.99/year`

Estimated monthly recurring cost for a serious WordPress-based Corpershub rebuild:

| Component | First-term estimate | Renewal estimate | Notes |
| --- | ---: | ---: | --- |
| GoDaddy VPS `4 vCPU / 8 GB` | $34.99 | $49.99 | more realistic than basic plans |
| SSL | $0.00 | $10.00 | based on about `$119.99/year` |
| Domain | $0.00 to $1.83 | $1.83 | later use domain renewal estimate |
| Commercial plugin stack | $60 to $250 | $60 to $250 | inference |
| Email and misc SaaS | $5 to $30 | $5 to $30 | inference |
| Extra admin/monitoring tools | $0 to $25 | $0 to $25 | inference |

Expected total:

- First term: about **$100 to $342/month**
- Renewal: about **$127 to $367/month**

This is cheaper than fully managed VPS, but now you own far more of the operational burden.

### Scenario E: Full WordPress Replatform On GoDaddy Fully Managed VPS

Official pricing reviewed:

- GoDaddy fully managed VPS `4 vCPU / 8 GB`: `$124.99/mo` first term, auto-renews at about `$139.99/mo`
- GoDaddy fully managed VPS `4 vCPU / 16 GB`: `$134.99/mo` first term
- SSL renewal shown at `$119.99/year`

Estimated monthly recurring cost:

| Component | First-term estimate | Renewal estimate | Notes |
| --- | ---: | ---: | --- |
| GoDaddy fully managed VPS `4 vCPU / 8 GB` | $124.99 | $139.99 | official reviewed pricing |
| SSL | $0.00 | $10.00 | after first year |
| Domain | $0.00 to $1.83 | $1.83 | later use domain renewal estimate |
| Commercial plugin stack | $60 to $250 | $60 to $250 | inference |
| Email and misc SaaS | $5 to $30 | $5 to $30 | inference |
| Extra services | $0 to $25 | $0 to $25 | inference |

Expected total:

- First term: about **$190 to $432/month**
- Renewal: about **$217 to $457/month**

This is operationally easier than self-managed VPS, but by this point the WordPress/GoDaddy route is no longer especially cheap.

## One-Time Replatform Cost

This is the part that matters most.

For the current codebase, moving the full application to WordPress is not a hosting migration. It is a rebuild of:

- authentication and role logic
- profile and verification workflows
- search/privacy logic
- chat
- payments and webhook flows
- admin operations

Planning estimate only, based on the visible codebase complexity:

- likely **4 to 8 engineer-months minimum**
- likely **$20,000 to $120,000+** one-time delivery cost depending on team, geography, and scope discipline

This is an inference from the repo structure and feature set, not a vendor quote.

## Advantages Of Deploying To WordPress

### WordPress advantages

| Advantage | Why it helps |
| --- | --- |
| Low hosting entry cost | marketing and brochure sites are very cheap to launch |
| Large plugin ecosystem | many common website features can be added quickly |
| Good CMS/editor experience | non-technical teams can publish and update content easily |
| Strong SEO tooling | blogs, landing pages, and content marketing are straightforward |
| Large hiring pool | easier to find WordPress developers than niche-stack specialists |

### GoDaddy advantages

| Advantage | Why it helps |
| --- | --- |
| Simple bundled purchasing | domain, hosting, SSL, email, and basic security can be bought in one place |
| Easy onboarding | beginner-friendly setup for small content sites |
| Managed WordPress convenience | backups, SSL, WAF, and malware scanning are bundled on managed plans |
| Support availability | GoDaddy promotes 24/7 support and a large support operation |

## Disadvantages Of Deploying To WordPress

### WordPress disadvantages for Corpershub

| Disadvantage | Why it matters here |
| --- | --- |
| Wrong fit for current stack | this repo is not PHP/WordPress and cannot be lifted into WordPress hosting |
| Full replatform required | the core product would need to be rebuilt, not simply deployed |
| Weak fit for real-time app behavior | chat, background jobs, and queue-driven workflows are much less natural in WordPress |
| Plugin dependency risk | critical workflows become dependent on third-party plugins and plugin compatibility |
| Security surface grows | more plugins usually means more patching and more vulnerability exposure |
| Harder product evolution | custom business logic becomes harder to reason about than in a dedicated app stack |
| Privacy/compliance complexity | the app handles sensitive profile data and WordPress is a weaker base for that kind of custom control |

### GoDaddy disadvantages for Corpershub

| Disadvantage | Why it matters here |
| --- | --- |
| Promo pricing can be misleading | first-term pricing is much lower than renewal pricing |
| Managed WordPress is not app hosting | it is optimized for WordPress sites, not a real-time custom product like this one |
| VPS is regionally opaque for Nigeria performance | GoDaddy’s reviewed pages emphasize global data centers but not a Nigeria-specific latency strategy |
| Less cloud-native flexibility | compared with AWS or similar platforms, infra automation, queueing, and service composition are less natural |
| Custom app ops still become your problem | once you move beyond basic WordPress, much of the simplicity benefit disappears |

## Recommendation

For Corpershub, WordPress on GoDaddy is a good option only for:

- a content site
- a landing site
- SEO pages
- blog/news pages

It is not a good primary platform for the actual application.

Recommended path if WordPress is still desired:

1. Keep the application on the app-oriented architecture already recommended.
2. Use WordPress on GoDaddy only for public content if needed.
3. Avoid a full WordPress rebuild unless there is a strategic reason to change the product stack completely.

## Sources

- GoDaddy Managed Hosting for WordPress: <https://www.godaddy.com/hosting/wordpress-hosting>
- GoDaddy WordPress hosting pricing snippet with first-term and renewal amounts: <https://www.godaddy.com/hosting/ecommerce-hosting>
- GoDaddy self-managed VPS hosting: <https://www.godaddy.com/hosting/vps-hosting>
- GoDaddy fully managed VPS hosting: <https://www.godaddy.com/hosting/fully-managed-vps-hosting>
- GoDaddy domain pricing pages: <https://www.godaddy.com/domains>
- GoDaddy pricing overview: <https://www.godaddy.com/pricing>
- WordPress.com pricing benchmark: <https://wordpress.com/pricing/>
