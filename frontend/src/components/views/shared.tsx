import { type ReactNode } from 'react';
import { Activity } from 'lucide-react';
import { LeaderboardChanges } from '@/types';
export const todayString = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}
export const durationLabel = (seconds: number | null | undefined) => {
  if (!seconds) return '—';
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  if (!minutes) return `${remainder} sec`;
  return remainder ? `${minutes} min ${remainder} sec` : `${minutes} min`;
}
export const niceDate = (value: string | null | undefined) => value ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—'
export const nicePeriod = (p: string) => p === 'morning' ? 'Morning' : 'Evening'

export function LoadingSkeleton() {
  return <main className="route-skeleton" role="status" aria-label="Loading OneMoreRep">
    <header className="skeleton-topbar"><div className="skeleton-brand"><span className="skeleton-shape skeleton-logo"/><span className="skeleton-brand-copy"><i className="skeleton-shape"/><i className="skeleton-shape"/></span></div><div className="skeleton-tools"><i className="skeleton-shape"/><i className="skeleton-shape"/></div></header>
    <div className="skeleton-workspace"><aside className="skeleton-sidebar"><i className="skeleton-shape skeleton-label"/>{Array.from({length:7},(_,i)=><i className="skeleton-shape skeleton-nav-row" key={i}/>)}</aside>
      <section className="skeleton-content"><div className="skeleton-heading"><div><i className="skeleton-shape skeleton-label"/><i className="skeleton-shape skeleton-title"/><i className="skeleton-shape skeleton-subtitle"/></div><i className="skeleton-shape skeleton-action"/></div>
        <div className="skeleton-metrics">{Array.from({length:3},(_,i)=><div className="skeleton-shape skeleton-metric" key={i}/>)}</div>
        <div className="skeleton-columns"><section className="skeleton-shape skeleton-panel"><i className="skeleton-shape skeleton-panel-title"/><i className="skeleton-shape skeleton-line"/><i className="skeleton-shape skeleton-line short"/><i className="skeleton-shape skeleton-line"/></section><section className="skeleton-shape skeleton-panel"><i className="skeleton-shape skeleton-panel-title"/><i className="skeleton-shape skeleton-line"/><i className="skeleton-shape skeleton-line"/><i className="skeleton-shape skeleton-line short"/></section></div>
      </section>
    </div>
  </main>;
}

export function initials(name: string) { return name.trim().split(/\s+/).slice(0, 2).map((s) => s[0]?.toUpperCase() || '').join(''); }

export function describeLeaderboardChanges(item:LeaderboardChanges) {
  const values:[string,number][]=[['Total EXP',item.amount],['This week',item.weekly_amount],['This month',item.monthly_amount],['Streak',item.current_streak_delta],['Best streak',item.longest_streak_delta],['Workouts',item.workout_delta]];
  return values.filter(([,amount])=>amount!==0).map(([label,amount])=>`${label} ${amount>0?'+':''}${amount}`).join(' · ');
}

export function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow:string; title:string; subtitle:string; action?:ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

export function MetricCard({ icon:Icon, label, value, note, tone='navy' }: { icon:typeof Activity; label:string; value:string|number; note:string; tone?:string }) {
  return <div className="metric-card"><span className={`metric-icon ${tone}`}><Icon size={19} /></span><span className="metric-label">{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

export function EmptyState({ icon:Icon, title, text, action, onClick }: { icon:typeof Activity; title:string; text:string; action?:string; onClick?:()=>void }) {
  return <div className="empty-state"><span><Icon size={21}/></span><b>{title}</b><p>{text}</p>{action&&<button className="secondary-button" onClick={onClick}>{action}</button>}</div>;
}
