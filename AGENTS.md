# Правила работы агентов

## NEXUS architecture
- App Router Server Components read Supabase; action modules own mutations. Reuse Shell/PostCard/Compose/Submit. Validate input and authenticate every action.
- `lib/supabase.ts` uses the publishable key and cookies; `proxy.ts` refreshes sessions. Never add service-role keys to browser or app code.
- `supabase/migrations/` mirrors the applied backend history. Add new migrations and RLS tests; never edit/reapply an existing migration.
- Keep all content as escaped text. Do not add simulated data, AI, media or navigation features presented as working.
- Update PROGRESS.md with actual checks and blockers after each milestone. Email delivery must be verified before public launch; confirmed synthetic accounts do not prove SMTP delivery.
- NEXUS uses only gorikandgozik-svj/proba and Supabase whxtdqwtjwauinpbbrrq. Do not cross-connect unrelated repositories or backends.

- Перед изменением кода прочитайте файлы, относящиеся к задаче, и существующие инструкции проекта.
- Сохраняйте текущую архитектуру и используйте установленные библиотеки. Добавляйте зависимость только при конкретной необходимости; объясняйте её в PR.
- Делайте минимальные, но законченные изменения. Не меняйте несвязанные файлы и не создавайте демонстрационные функции без запроса.
- Не выдавайте заглушки или фиктивные реализации за работающий результат.
- Перед сдачей запускайте `npm run typecheck`, `npm run lint`, `npm test` и `npm run build`. Если проверка недоступна, укажите причину и последствия.
- Фиксируйте найденные ошибки и ограничения в отчёте или PR; не скрывайте падения проверок.
- Не добавляйте секреты, токены, ключи API или `.env` файлы в репозиторий. Используйте переменные окружения.
- Не удаляйте данные, ветки или репозитории и не выполняйте force push.
- Работайте в feature-ветке от `main`. Для готовых изменений создавайте pull request, когда права позволяют.
- Не устанавливайте дополнительные инструменты и сервисы без обоснованной необходимости.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
