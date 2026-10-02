const sections = [
  'feed', 'activity', 'progress', 'friends', 'history', 'exp',
  'leaderboard', 'statistics', 'profile', 'admin',
];

export function generateStaticParams() {
  return sections.map((section) => ({ section }));
}

export default function DashboardSectionPage() {
  return null;
}
