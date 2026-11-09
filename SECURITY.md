# Security and release boundaries

NEXUS is ready for controlled development and adult testing. Public consumer launch requires operator review and operational setup.

- Every exposed application table has RLS. Server mutations verify the authenticated user and validate untrusted input. No service-role credential is used by the app. Private helpers use an empty search path and explicit execution grants.
- Posts/comments/messages have database cooldowns. Other writes and uploads have durable per-account minute budgets. Supabase Auth provides its own authentication limits. These controls do not replace a WAF, CAPTCHA, abuse monitoring or quota alerts for a public release.
- Image/video uploads check size, accepted MIME types and magic bytes; the private bucket also enforces MIME/size limits and owner folder paths. The app does not scan for malware, transcode video or certify uploaded content. Playback depends on the browser's codec support.
- Storage downloads use signed URLs valid for five minutes. Blocking prevents issuing new links to blocked content, but cannot revoke a previously issued link before expiry or retract previously downloaded data.
- Conversation reads and writes require membership. A block prevents new messages between the accounts. There is no end-to-end encryption. Project administrators retain backend access.
- Reports are stored privately for the operator to review in Supabase. Before public launch, establish a review process, escalation and takedown handling, an age policy, retention policy, and self-service export/deletion or a staffed request channel.
- Supabase's security advisor reports leaked-password protection as disabled. Review https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection and available account-plan support; no paid upgrade has been enabled. Email confirmation stays enabled. Real delivery and SMTP are not certified by our synthetic-account tests.
- The scoped npm override of `minimatch` to 11.0.5 addresses GHSA-g3hv-75wg-m249 in the lint toolchain. Remove it once typescript-eslint's supported dependency range includes the fix. CI verifies compatibility with the current project.

Do not publish real user data, change billing, or deploy publicly without explicit authorization. Do not connect other repositories or Supabase projects to NEXUS.
