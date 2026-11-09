# Running NEXUS in the cloud

Use Node.js 26 and npm. This is a Next.js server application; a static file host is not sufficient.

## Codex Cloud development

Create an environment for **gorikandgozik-svj/proba**, branch **main** after the MVP PR is merged (or use the PR branch before merge). Setup command: `npm ci`. Add the following project-specific variables using the environment settings:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://whxtdqwtjwauinpbbrrq.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<publishable key from the NEXUS project's Connect dialog>
```

The publishable key is deliberately absent from Git. A service-role key or OpenAI API key is unnecessary. Run `npm run check` for verification and `npm run dev` for an interactive development server. Saved Codex Cloud environment creation could not be completed by the available tools; no environment has been silently provisioned.

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
