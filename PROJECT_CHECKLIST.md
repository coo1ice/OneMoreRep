# OneMoreRep project checklist

Audit date: 2026-10-03. This records what is present in this checkout, what passed local checks, and what still needs a live deployment check. A checkmark means the source implements the item; it does not by itself prove the deployed site is using it.

## Product and original brief

- [x] Deliver a website instead of the original desktop/Tkinter application.
- [x] Use PostgreSQL instead of the original MySQL request. The database bootstrap checks for an empty database and refuses incompatible partial schemas instead of dropping existing data.
- [x] Keep the AAKAR project untouched; its colors/layout were used only as inspiration.
- [x] Provide registration/login, password hashing, sessions, private activity history, statistics, achievements, EXP, streaks, and error handling in the web app.
- [x] Document local setup and Vercel/Supabase deployment in `README.md`.

## Requested features

- [x] Strength, walking, and sports workout logging; morning EXP window 05:00–10:00 and evening window 17:00–22:00.
- [x] Progress reports with date, notes, and optional fitness photo; no required weight field.
- [x] Optional workout photos and a feed control for including the photo when sharing a workout.
- [x] Private friend feed with workout and achievement posts, likes, comments, and group management.
- [x] Friend and group leaderboards; no global all-users leaderboard in the user-facing leaderboard.
- [x] Dashboard friend-request actions and dashboard friend-feed preview.
- [x] Users can delete their own posts/comments and activity/progress records; admin endpoints allow authorized moderation of member data.
- [x] Admin console and server-side role checks; admin can view/edit/delete members’ records, adjust EXP and leaderboard values, and manage member data.
- [ ] The source does not automatically promote `souptik` and `coolice` to admin. Promote those accounts in the deployed PostgreSQL database using the documented admin procedure and verify both roles after sign-in.
- [x] Client-side image resizing/compression plus server-side 2 MB upload cap for JPEG, PNG, and WebP.
- [x] Theme uses the requested charcoal/steel, lime, and orange colors; provided logo is used in the app and favicon.
- [x] Mobile breakpoints, skeleton loading states, route-specific URLs, and reduced-motion handling are present.
- [ ] Remove all redundant explanatory/privacy copy everywhere: reduced in the profile and image-upload copy, but a complete visual/content sweep has not been verified.

## Bugs and deployment

- [x] Fix the PostgreSQL leaderboard streak aggregation error.
- [x] Fix the statistics SQL placeholder mismatch and include a regression test.
- [x] Configure exported clean URLs for top-level pages such as `/login` and `/statistics`.
- [x] Add an empty Next not-found page so the framework's default 404 does not render beneath the client-routed app shell when scrolling. This latest fix is only in the local checkout; it has not been pushed or confirmed on Vercel.
- [x] Vercel API entry point, static frontend output, Supabase PostgreSQL/Storage configuration guidance, and upload storage integration are present in source/docs.
- [ ] Verify production and preview Vercel environment variables, current Supabase credentials/storage bucket, and a successful live sign-in, API request, and image upload. The user previously reported configuring these, but this audit did not access their secrets or exercise production.
- [ ] Push and redeploy the latest local changes (including the not-found fix, backfill streak fix, this checklist, and documentation cleanup) before considering the live 404 issue closed.

## Issues found in this audit

- [x] Backdated workouts still qualify for EXP, but are now excluded from current and longest streak calculations. A safe PostgreSQL migration adds `workouts.streak_eligible` with a true default for existing records; new backdated entries are marked false. A unit regression test checks that a backfill cannot bridge a broken streak.
- [ ] Confirm that admin leaderboard adjustments and data-management actions work against the deployed database, not only in source.
- [ ] Complete a deployed mobile/browser visual pass after redeployment. This audit verified code and local build/type/lint checks, not every interaction in production.

## Verification run for this audit

- [x] `python -m unittest discover -s tests -v` after the backfill streak fix — 9 passed; 1 PostgreSQL integration test skipped because `ONEMOREREP_TEST_DATABASE=1` was not enabled.
- [x] `npm run lint` — passed.
- [x] `npx tsc --noEmit` — passed.
- [x] Static export generation was previously verified locally; the normal Next build hit a Windows `spawn EPERM` worker error in this environment. A successful Vercel build was reported earlier, before the latest local not-found change.
- [ ] PostgreSQL integration test against the actual hosted deployment — not run.

## Superseded requirements

The pasted starting brief requested a Python desktop app backed by MySQL. Later directions explicitly changed the product to a deployable website using PostgreSQL, so the desktop UI and MySQL-specific setup are intentionally not checklist failures.
