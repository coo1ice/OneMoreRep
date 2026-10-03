import { useState } from 'react';
import { Activity, Check, ChevronRight, Dumbbell, Footprints, Flame, Plus, ShieldCheck, Sparkles, Trophy, Users, X } from 'lucide-react';
import { Dashboard, FeedPost, FriendRequest, Workout } from '@/types';
import type { View } from '@/components/views/types';
import { initials, PageHeading, MetricCard, EmptyState, durationLabel, niceDate } from '@/components/views/shared';
import { FeedCard } from '@/components/views/feed';
export function DashboardView({ data, workouts, posts, friendRequests, userId, onDeletePost, onRespondFriend, onNavigate }: { data:Dashboard|null; workouts:Workout[]; posts:FeedPost[]; friendRequests:FriendRequest[]; userId:number; onDeletePost:(id:number)=>void; onRespondFriend:(id:number,accept:boolean)=>Promise<void>; onNavigate:(v:View)=>void }) {
  const current = data?.streak?.current_streak ?? 0;
  return <><PageHeading eyebrow="YOUR PROGRESS" title={`Good to see you${data?.name ? `, ${data.name.split(' ')[0]}` : ''}.`} subtitle="A little consistency adds up. Here’s how you’re doing." action={<button className="primary-button" onClick={() => onNavigate('activity')}><Plus size={17} /> Log activity</button>} />
    <section className="metric-grid"><MetricCard icon={Flame} label="Current streak" value={`${current} days`} note={`Personal best · ${data?.streak?.longest_streak ?? 0} days`} tone="orange" /><MetricCard icon={Sparkles} label="Total EXP" value={(data?.total ?? 0).toLocaleString()} note="Every qualifying session counts" tone="green" /><MetricCard icon={Trophy} label="Today’s EXP" value={`${data?.today ?? 0} / 50`} note="Daily cap · 30 morning + 20 evening" /><MetricCard icon={Users} label="Friends rank" value={data?.rank ? `#${data.rank}` : '—'} note="Among all your friends" tone="blue" /></section>
    {friendRequests.length>0&&<DashboardFriendRequests requests={friendRequests} onRespond={onRespondFriend} onViewFriends={()=>onNavigate('friends')}/>}
    <div className="dashboard-grid"><section className="panel today-panel"><div className="panel-heading"><div><span className="panel-kicker">TODAY</span><h2>Your daily check-in</h2></div><span className="date-chip">{new Date().toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}</span></div><PeriodStatus icon="🌅" label="Morning" points={30} amount={data?.morning ?? 0} duration={data?.morning_duration ?? 0} /><PeriodStatus icon="🌆" label="Evening" points={20} amount={data?.evening ?? 0} duration={data?.evening_duration ?? 0} /><div className="daily-footnote"><ShieldCheck size={15} /> One qualifying session per period · 50 EXP maximum per day</div></section>
      <section className="panel activity-panel"><div className="panel-heading"><div><span className="panel-kicker">RECENT WORK</span><h2>Latest activity</h2></div><button className="text-button" onClick={() => onNavigate('history')}>View history <ChevronRight size={15} /></button></div>{workouts.slice(0,4).map((w)=><WorkoutRow key={w.id} workout={w} />)}{!workouts.length && <EmptyState icon={Activity} title="Your story starts here" text="Log your first activity to start building momentum." action="Log activity" onClick={()=>onNavigate('activity')} />}</section></div>
    <section className="panel mini-feed"><div className="panel-heading"><div><span className="panel-kicker">YOUR GROUP</span><h2>Friends feed</h2></div><button className="text-button" onClick={()=>onNavigate('feed')}>Open feed <ChevronRight size={15} /></button></div>{posts.length ? <div className="mini-feed-list">{posts.map(p=><FeedCard key={p.id} post={p} currentUserId={userId} onDeletePost={onDeletePost} />)}</div> : <div className="friend-empty"><Users size={20}/><span>Your friends’ shared workouts will show here.</span><button className="text-button" onClick={()=>onNavigate('friends')}>Find friends <ChevronRight size={15}/></button></div>}</section>
  </>;
}

export function DashboardFriendRequests({requests,onRespond,onViewFriends}:{requests:FriendRequest[];onRespond:(id:number,accept:boolean)=>Promise<void>;onViewFriends:()=>void}) {
  const [busyId,setBusyId]=useState<number|null>(null);
  async function respond(id:number,accept:boolean) {
    setBusyId(id);
    try { await onRespond(id,accept); }
    finally { setBusyId(null); }
  }
  return <section className="panel request-panel dashboard-requests"><div className="panel-heading"><div><span className="panel-kicker">YOUR CIRCLE</span><h2>Friend requests <span className="count-pill">{requests.length}</span></h2></div><button className="text-button" onClick={onViewFriends}>View friends <ChevronRight size={15}/></button></div><div className="friend-list">{requests.map(request=><div className="friend-row request-row" key={request.id}><span className="avatar">{initials(request.display_name)}</span><div><b>{request.display_name}</b><small>@{request.username}</small></div><div className="request-actions"><button className="accept-button" disabled={busyId!==null} aria-label={`Accept ${request.display_name}`} onClick={()=>void respond(request.id,true)}><Check size={15}/></button><button className="decline-button" disabled={busyId!==null} aria-label={`Decline ${request.display_name}`} onClick={()=>void respond(request.id,false)}><X size={15}/></button></div></div>)}</div></section>;
}

export function PeriodStatus({ icon, label, points, amount, duration }: { icon:string; label:string; points:number; amount:number; duration:number }) {
  const complete=amount>0;
  const hour=new Date().getHours();
  const notStarted=!complete&&(label==='Morning'?hour<5:hour<17);
  const summary=complete?`${durationLabel(duration)} · +${amount} EXP earned`:duration>0?`${durationLabel(duration)} logged · no EXP earned`:'No activity logged yet';
  return <div className="period-row"><span className="period-emoji">{icon}</span><div className="period-copy"><b>{label}</b><small>{notStarted?'This period has not started':summary}</small></div><span className={`period-status ${complete?'complete':''}`}>{complete ? <><Check size={14}/> +{points} EXP</> : notStarted?'Not started':'Not completed'}</span></div>;
}

export function WorkoutRow({ workout }: { workout:Workout }) {
  const isStrength=workout.workout_type==='Strength';
  const icon=isStrength?<Dumbbell size={17}/>:workout.workout_type==='Walking'?<Footprints size={17}/>:<Activity size={17}/>;
  return <div className="workout-row"><span className={`workout-kind ${isStrength?'kind-strength':'kind-walk'}`}>{icon}</span><div className="workout-copy"><b>{workout.workout_type}</b><small>{niceDate(workout.workout_date)} · {workout.start_time?.slice(0,5) || '—'}{workout.has_image?' · Photo attached':''}</small></div><span className="workout-duration">{durationLabel(workout.duration)}</span><span className={`xp-chip ${workout.exp_amount?'xp-earned':''}`}>{workout.exp_amount?`+${workout.exp_amount} EXP`:'0 EXP'}</span></div>;
}
