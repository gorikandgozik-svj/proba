# NEXUS progress

## Implemented
- Phase 1 integration: password signup/login/logout, email confirmation endpoint, profile upsert, text publishing, newest-first Mixed/Following feeds, search, likes, comments, follow/unfollow.
- Responsive UI, OS dark/light themes, focus states, empty/loading/error states.
- Dedicated Supabase nexus project; 5 tables, constraints, indexes, RLS and posting cooldown triggers deployed with nexus_phase1 migration. No service-role key in app.
- `.env.local` configured locally and ignored; cloud environment variables still require configuration.

## Verified
- TypeScript, ESLint, 3 Node tests and production build passed.
- Live Postgres transaction: two synthetic users, profiles/post/reaction/comment/follow; cross-user profile update and author spoof denied; anonymous read denied; cooldown enforced. All test data rolled back.
- Supabase security advisor returned no findings.
- Browser: login screen, failed-password feedback, desktop and mobile layout without horizontal overflow.

## Blockers / limits
- Full signup → confirmation email → authenticated browser journey has not been verified. Configure Supabase Auth Site URL and confirmation template, then use a real email address.
- No public deployment. Image uploads are not enabled. Phase 2+ intentionally pending until Phase 1 E2E passes.
- npm reports 8 moderate dependency vulnerabilities (existing toolchain). ESLint 9 is retained for Next config compatibility; update with verified ecosystem support.
- SQL assertions impersonate roles for database testing; they do not prove Auth signup/login behavior.

## Next milestone
Complete real email E2E with two accounts, test authenticated mobile flows, add image upload with private storage policies, improve feed pagination and moderation before public deployment.
