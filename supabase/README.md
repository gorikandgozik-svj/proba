# Database migrations

The files in `migrations/` reproduce the actual migration versions applied to the dedicated NEXUS project (`whxtdqwtjwauinpbbrrq`). Apply them in filename order to a new empty Supabase project. Do not reapply SQL to the existing NEXUS backend.

For a future change, use the Supabase CLI migration workflow (create with `supabase migration new <name>`, inspect, test, then deploy), or the connected Supabase migration tool and sync its actual version here. Do not edit already-applied migrations. This application does not require running Docker or Postgres on a developer's Windows PC.

`tests/rls.sql` is a transactional database smoke test, not a migration. Integration scripts exercise the real Auth/Data/Storage APIs with explicitly provisioned synthetic accounts. Never run those scripts with personal accounts.

The private `nexus-media` bucket is created by the media migration. Files remain private; signed download links last five minutes. Database rows are removed by account cascades, but Storage object cleanup must also use the Storage API. Never delete Storage metadata using raw SQL.
