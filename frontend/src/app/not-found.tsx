/**
 * The application is a client-routed SPA. Its shared app shell handles unknown
 * URLs by redirecting to /login or /dashboard, so rendering Next's default 404
 * here would append a second page below that shell.
 */
export default function NotFound() {
  return null;
}
