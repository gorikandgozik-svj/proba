# NEXUS — implementation status

## Completed
- Unified Phase 1–3 developer MVP: accounts/profiles, text/photo/video posts, reactions/comments/follows/search, community feeds and membership, bookmarks, hidden posts, explicit interests, notifications, reports, blocks, direct/group messages.
- Adaptive feed modes with explainable ranking and pagination; responsive navigation; system/light/dark appearance; real pending, empty, error and loading states.
- Dedicated Supabase nexus backend, versioned migrations synced from its actual history, private media bucket, RLS, indexes, ownership constraints, member-only conversations, cooldowns and durable write budgets.
- PKCE and token-hash email confirmation handlers. No AI-provider calls, public hosting, paid services or unrelated-project changes.

## Verified during implementation
- Final local `npm run check` passed: strict TypeScript, ESLint without warnings, 5 unit tests and production build after dependency hardening.
- Real Auth login with three synthetic confirmed users. Browser: profile creation, publishing, refresh persistence, like/comment, follow and Following feed.
- Live API integration: community membership, bookmarks, preferences, private reports, recipient-only notifications, hide/restore and mutual blocks.
- Live API integration: direct/group messages; outsider reads/writes denied; direct conversations capped at two; member cap enforced; blocked contact denied.
- Private Storage: upload/download, signed URL, owner-path restriction, anonymous denial, blocked-user denial and attachment-owner spoof denial.
- Browser: upload and play a real 10-second MP4, create persistent conversation/message, create community, save preferences, responsive seven-item navigation and theme persistence.
- Production dependency audit clean; scoped minimatch override also removed the lint-toolchain advisories. No service-role credential in application code or Git.

## Release boundaries
- Synthetic test users are provisioned as confirmed users for automated Auth/browser tests. Actual signup email delivery is not proven by those tests; configure and verify SMTP and Auth redirects before open registration.
- Supabase warns that leaked-password protection is disabled. No paid upgrade was enabled. Review SECURITY.md.
- No public deployment. Saved Codex Cloud environment could not be created: the available native browser tool stopped because it could not confidently identify the current Windows browser URL. The GitHub repository and backend are ready; DEPLOYMENT.md contains the exact environment configuration.
- Moderation operations, age/retention policy and account deletion/export requests require an operator process before a public launch. Signed media URLs remain valid until expiry; no end-to-end encryption or transcoding is claimed.
- Synthetic QA records and Storage files are cleaned up before delivery; source contains no seeded demo content or test credentials.
