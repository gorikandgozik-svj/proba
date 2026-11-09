# Правила работы агентов

## NEXUS architecture
- App Router Server Components read Supabase; `app/actions.ts` owns mutations. Validate inputs in `lib/validation.mjs` and authenticate every action.
- `lib/supabase.ts` uses the publishable key and cookies; `proxy.ts` refreshes sessions. Never add service-role keys to browser or app code.
- `db/phase1.sql` is the already-applied initial schema. Future changes require new migrations and RLS tests, never rerun this file on an existing database.
- Keep all content as escaped text. Do not add simulated data, AI, media or navigation features presented as working.
- Update PROGRESS.md with actual checks and blockers after each milestone. Phase 2 starts only after real email E2E verification.

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
