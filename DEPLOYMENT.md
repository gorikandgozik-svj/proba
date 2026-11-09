# Running NEXUS in the cloud

Use Node.js 26 and npm. This is a Next.js server application; a static file host is not sufficient.

## Codex Cloud development

Select the saved **proba** environment in Codex → Cloud. It is active and private (Only me), uses only **gorikandgozik-svj/proba**, branch **main**, and has the NEXUS backend variables configured. Its setup installs checksum-verified Node.js 26.13.0 and runs `npm ci` with a shared npm cache. The following variables describe the configuration if the environment ever needs to be recreated:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://whxtdqwtjwauinpbbrrq.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<publishable key from the NEXUS project's Connect dialog>
```

The publishable key is deliberately absent from Git. A service-role key or OpenAI API key is unnecessary. Run `npm run check` for verification and `npm run dev` for an interactive development server. The environment was saved and activated on 2026-11-09; the app API confirmed `runnable: true`. Startup instructions select the installed Node runtime, read AGENTS.md / PROGRESS.md, and preserve checkpoints. Package-manager domains plus nodejs.org and the dedicated NEXUS Supabase domain are allowed; unrestricted internet remains off. NEXT_TELEMETRY_DISABLED=1 is configured. Service usage and session limits still apply; this configuration does not guarantee uninterrupted seven-day execution.

## Hosting preparation

Use a host that supports the selected Next.js version and Node 26. Set the two variables above at build and runtime. Set `NEXT_PUBLIC_APP_URL` to the exact HTTPS origin for uploads. Commands:

```bash
npm ci
npm run check
npm start -- --hostname 0.0.0.0
```

The host must support request bodies of at least 26 MB for the configured video limit. If its request-body limit is lower, reduce the app's upload limit or implement direct-to-Storage upload tickets with equivalent validation before deployment. Do not assume a free host supports this limit.

Set the Supabase Auth Site URL and redirect allowlist to the application origin. The app supports both the default PKCE `?code=` confirmation redirect and the optional custom `/auth/confirm?token_hash={{ .TokenHash }}&type=email` template. Configure a real SMTP provider and verify delivery, confirmation, login, profile editing and posting with two test accounts before opening registration to the public. Evaluate current hosting/SMTP quotas before selecting a plan. No hosting account or paid infrastructure has been added.

Review SECURITY.md before launch. Previewing in a developer sandbox does not establish public-launch readiness.
