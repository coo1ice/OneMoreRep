'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import {
  Activity, Award, BarChart3, Camera, Check, ChevronRight, Clock3, Dumbbell,
  Footprints, Flame, Heart, ImagePlus, LayoutDashboard, LoaderCircle, LogOut,
  Menu, Plus, Send, ShieldCheck, Sparkles, Trophy, UserPlus, UserRound, Users, X, Trash2,
} from 'lucide-react';
import { API_BASE, api } from '@/lib/api';
import { prepareImage } from '@/lib/image';
import type { Achievement, AdminAccount, AdminReport, Dashboard, ExpRecord, FeedComment, FeedPost, Friend, FriendGroup, FriendList, FriendRequest, LeaderboardChanges, LeaderboardRow, ProgressReport, Statistics, User, Workout, WorkoutDetail } from '@/types';

type View = 'dashboard' | 'feed' | 'activity' | 'progress' | 'friends' | 'history' | 'exp' | 'leaderboard' | 'statistics' | 'profile' | 'admin';
type Exercise = { exercise_name: string; weight: string; reps: string; sets: string };

const nav: { id: View; label: string; icon: typeof Activity }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'feed', label: 'Friends feed', icon: Users },
  { id: 'activity', label: 'New activity', icon: Plus },
  { id: 'progress', label: 'Progress reports', icon: Activity },
  { id: 'history', label: 'History', icon: Clock3 },
  { id: 'exp', label: 'EXP history', icon: Sparkles },
  { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'friends', label: 'Friends', icon: UserPlus },
  { id: 'profile', label: 'Profile', icon: UserRound },
];

const todayString = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};
const durationLabel = (seconds: number | null | undefined) => {
  if (!seconds) return '—';
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  if (!minutes) return `${remainder} sec`;
  return remainder ? `${minutes} min ${remainder} sec` : `${minutes} min`;
};
const niceDate = (value: string | null | undefined) => value ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
const nicePeriod = (p: string) => p === 'morning' ? 'Morning' : 'Evening';
const routeView = (pathname: string): View => {
  const section = pathname.split('/')[1] as View | undefined;
  if (!section) return 'dashboard';
  if (section === 'dashboard' || section === 'admin' || nav.some(({ id }) => id === section)) return section;
  return 'dashboard';
};
const isAppRoute = (pathname: string) => pathname === '/dashboard' || pathname === `/${routeView(pathname)}`;

export function OneMoreRepApp() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const view = routeView(pathname);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const initialDashboardLoaded = useRef(false);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [expRows, setExpRows] = useState<ExpRecord[]>([]);
  const [friendList, setFriendList] = useState<FriendList | null>(null);
  const [groups, setGroups] = useState<FriendGroup[]>([]);
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [progressReports, setProgressReports] = useState<ProgressReport[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminAccount[]>([]);
  const loadAdminUser = useCallback((id:number) => api.adminReport(id), []);
  const reloadAdminUsers = useCallback(async () => { const rows=await api.adminUsers(); setAdminUsers(rows); return rows; }, []);

  useEffect(() => {
    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.has('password')) {
      currentUrl.searchParams.delete('username');
      currentUrl.searchParams.delete('password');
      window.history.replaceState(window.history.state, '', `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
    }
    api.bootstrap().then((initial) => {
      setDashboard(initial.dashboard);
      setPosts(initial.feed);
      setWorkouts(initial.workouts);
      initialDashboardLoaded.current = true;
      setUser(initial.user);
      void api.friends().then(setFriendList).catch(() => setFriendList({incoming:[],outgoing:[],friends:[]}));
    }).catch(() => setUser(null)).finally(() => setBootstrapped(true));
  }, []);

  useEffect(() => {
    if (!bootstrapped) return;
    if (!user) {
      if (pathname !== '/login') router.replace('/login');
      return;
    }
    if (!isAppRoute(pathname) || (routeView(pathname) === 'admin' && user.role !== 'admin')) {
      router.replace('/dashboard');
      return;
    }
  }, [bootstrapped, pathname, router, user]);

  const loadView = useCallback(async (selected: View) => {
    if (!user) return;
    setBusy(true); setError('');
    try {
      if (selected === 'dashboard') {
        const [d, f, w, friends] = await Promise.all([api.dashboard(), api.feed(), api.workouts(), api.friends()]); setDashboard(d); setPosts(f); setWorkouts(w); setFriendList(friends);
      } else if (selected === 'feed') {
        const [f, w, a] = await Promise.all([api.feed(), api.workouts(), api.achievements()]); setPosts(f); setWorkouts(w); setAchievements(a);
      } else if (selected === 'activity' || selected === 'history') setWorkouts(await api.workouts());
      else if (selected === 'progress') setProgressReports(await api.progress());
      else if (selected === 'exp') setExpRows(await api.exp());
      else if (selected === 'friends') { const [f,g]=await Promise.all([api.friends(),api.groups()]);setFriendList(f);setGroups(g); }
      else if (selected === 'leaderboard') { const [g,l]=await Promise.all([api.groups(),api.leaderboard()]);setGroups(g);setLeaderboard(l); }
      else if (selected === 'statistics') setStats(await api.statistics());
      else if (selected === 'profile') { const [s, a] = await Promise.all([api.statistics(), api.achievements()]); setStats(s); setAchievements(a); }
      else if (selected === 'admin' && user.role === 'admin') setAdminUsers(await api.adminUsers());
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load this page.'); }
    finally { setBusy(false); }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    if (view !== routeView(pathname)) return;
    if (view === 'dashboard' && initialDashboardLoaded.current) {
      initialDashboardLoaded.current = false;
      return;
    }
    let cancelled = false;
    void Promise.resolve().then(() => { if (!cancelled) return loadView(view); });
    return () => { cancelled = true; };
  }, [user, view, pathname, loadView]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const signedIn = authMode === 'login'
        ? await api.login(String(form.get('username')), String(form.get('password')))
        : await api.register(String(form.get('username')), String(form.get('display_name')), String(form.get('password')));
      setUser(signedIn); router.replace('/dashboard');
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not sign in.'); }
    finally { setBusy(false); }
  }

  async function signOut() {
    try { await api.logout(); } finally { setUser(null); setNotice(''); router.replace('/login'); }
  }

  async function deleteOwnPost(id:number) {
    if (!window.confirm('Delete this post and its comments? This cannot be undone.')) return;
    try { await api.deletePost(id); setPosts(previous=>previous.filter(post=>post.id!==id)); setNotice('Your post was deleted.'); }
    catch (e) { setError(e instanceof Error?e.message:'Could not delete your post.'); }
  }

  async function deleteOwnWorkout(id:number) {
    if (!window.confirm('Delete this workout log and its attached photo? Your EXP and streak totals will be recalculated. This cannot be undone.')) return;
    try { await api.deleteWorkout(id); setNotice('Your workout was deleted.'); await loadView('history'); }
    catch (e) { setError(e instanceof Error?e.message:'Could not delete your workout.'); }
  }

  async function deleteOwnProgress(id:number) {
    if (!window.confirm('Delete this progress report and its attached photo? This cannot be undone.')) return;
    try { await api.deleteProgress(id); setNotice('Your progress report was deleted.'); await loadView('progress'); }
    catch (e) { setError(e instanceof Error?e.message:'Could not delete your progress report.'); }
  }

  function selectView(next: View) {
    setMobileNav(false); setError(''); setNotice('');
    router.push(next === 'dashboard' ? '/dashboard' : `/${next}`);
  }

  async function respondToFriendRequest(id:number,accept:boolean) {
    try {
      await api.respondFriend(id,accept);
      setFriendList(await api.friends());
      setNotice(accept?'Friend request accepted.':'Friend request declined.');
    } catch (e) { setError(e instanceof Error?e.message:'Could not update the friend request.'); }
  }

  if (!bootstrapped || (user && !isAppRoute(pathname)) || (!user && pathname !== '/login')) {
    return <LoadingSkeleton />;
  }

  if (!user) {
    return <AuthScreen mode={authMode} setMode={setAuthMode} onSubmit={submitAuth} busy={busy} error={error} />;
  }

  return (
    <div className="app-frame">
      <header className="topbar">
        <button className="mobile-menu icon-button" onClick={() => setMobileNav((v) => !v)} aria-label="Toggle navigation"><Menu size={21} /></button>
        <button className="brand" onClick={() => selectView('dashboard')} aria-label="OneMoreRep home">
          <Image className="brand-mark brand-logo" src="/onemorerep-logo.png" alt="" width={42} height={42} priority /><span className="brand-copy"><strong>OneMoreRep</strong><small>One more day. One more rep.</small></span>
        </button>
        <div className="topbar-right"><span className="private-pill"><ShieldCheck size={14} /> Friends only</span><span className="top-exp"><Sparkles size={15} /> {dashboard?.total?.toLocaleString() ?? '—'} EXP</span><button className="avatar" title={user.display_name}>{initials(user.display_name)}</button></div>
      </header>

      <div className="workspace">
        <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
          <div className="sidebar-label">YOUR SPACE</div>
          <nav aria-label="Main navigation">
            {[...nav, ...(user.role === 'admin' ? [{ id: 'admin' as const, label: 'Admin', icon: ShieldCheck }] : [])].map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${view === id ? 'nav-active' : ''}`} onClick={() => selectView(id)}><Icon size={18} strokeWidth={2} /><span>{label}</span>{id === 'feed' && <span className="nav-dot" />}</button>)}
          </nav>
          <div className="sidebar-bottom"><button className="nav-item logout-item" onClick={signOut}><LogOut size={18} /><span>Log out</span></button><div className="sidebar-user"><span className="avatar avatar-small">{initials(user.display_name)}</span><span><b>{user.display_name}</b><small>@{user.username}</small></span></div></div>
        </aside>
        {mobileNav && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}

        <main className="main-content">
          {notice && <div className="notice"><Check size={16} />{notice}<button onClick={() => setNotice('')} aria-label="Dismiss"><X size={15} /></button></div>}
          {error && <div className="error-banner">{error}<button onClick={() => setError('')} aria-label="Dismiss"><X size={15} /></button></div>}
          {busy && <div className="loading-line"><LoaderCircle size={16} className="spin" /> Loading your activity…</div>}
          <div key={view} className="view-transition">
            {view === 'dashboard' && <DashboardView data={dashboard} workouts={workouts} posts={posts.slice(0, 3)} friendRequests={friendList?.incoming??[]} userId={user.id} onDeletePost={deleteOwnPost} onRespondFriend={respondToFriendRequest} onNavigate={selectView} />}
            {view === 'feed' && <FeedView posts={posts} workouts={workouts} achievements={achievements} userId={user.id} onDeletePost={deleteOwnPost} onShare={async (form) => { const result = await api.share(form); setNotice('Shared with your friends.'); await loadView('feed'); return result.id; }} />}
            {view === 'activity' && <ActivityView onSave={async (payload, photo) => { const result = await api.createWorkout(payload, photo); setNotice(`Activity saved · ${durationLabel(result.duration_seconds)} · +${result.exp_earned} EXP`); await loadView('activity'); }} />}
            {view === 'progress' && <ProgressView reports={progressReports} onDelete={deleteOwnProgress} onSave={async (form) => { await api.saveProgress(form); setNotice('Progress report saved to your private records.'); await loadView('progress'); }} />}
            {view === 'friends' && <FriendsView data={friendList} groups={groups} onReload={() => loadView('friends')} onGroupsReload={() => loadView('friends')} onNotice={setNotice} />}
            {view === 'history' && <HistoryView rows={workouts} onShare={() => selectView('feed')} onDelete={deleteOwnWorkout} onDetails={(id) => api.activityDetail(id)} />}
            {view === 'exp' && <ExpView rows={expRows} />}
            {view === 'leaderboard' && <LeaderboardView rows={leaderboard} groups={groups} currentId={user.id} onSelectGroup={async(id)=>{setBusy(true);setError('');try{setLeaderboard(await api.leaderboard(id));}catch(e){setError(e instanceof Error?e.message:'Could not load leaderboard.');}finally{setBusy(false);}}} />}
            {view === 'statistics' && <StatisticsView data={stats} />}
            {view === 'profile' && <ProfileView user={user} stats={stats} achievements={achievements} onSignOut={signOut} />}
            {view === 'admin' && user.role === 'admin' && <AdminView users={adminUsers} actorId={user.id} onLoadUser={loadAdminUser} onReloadUsers={reloadAdminUsers} onAdjustLeaderboard={async(id,changes,reason)=>{await api.adminAdjustLeaderboard(id,changes,reason);setNotice('Leaderboard values updated.');}} />}
          </div>
        </main>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
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

function initials(name: string) { return name.trim().split(/\s+/).slice(0, 2).map((s) => s[0]?.toUpperCase() || '').join(''); }
function describeLeaderboardChanges(item:LeaderboardChanges) {
  const values:[string,number][]=[['Total EXP',item.amount],['This week',item.weekly_amount],['This month',item.monthly_amount],['Streak',item.current_streak_delta],['Best streak',item.longest_streak_delta],['Workouts',item.workout_delta]];
  return values.filter(([,amount])=>amount!==0).map(([label,amount])=>`${label} ${amount>0?'+':''}${amount}`).join(' · ');
}

function AuthScreen({ mode, setMode, onSubmit, busy, error }: { mode: 'login'|'register'; setMode:(mode:'login'|'register')=>void; onSubmit:(event:FormEvent<HTMLFormElement>)=>void; busy:boolean; error:string }) {
  return <main className="auth-page"><div className="auth-side"><Image className="brand-mark brand-logo auth-mark" src="/onemorerep-logo.png" alt="OneMoreRep" width={42} height={42} priority /><div className="auth-brand">OneMoreRep</div><div className="auth-badge"><Sparkles size={14} /> Small group. Big consistency.</div><h1>Your friends are moving.<br /><span>Move with them.</span></h1><p>Log activity, earn EXP, build a streak, and celebrate the work your friend group puts in.</p><div className="auth-mini-stats"><div><Flame size={18} /><b>Daily streaks</b></div><div><Trophy size={18} /><b>Friendly competition</b></div><div><Users size={18} /><b>Private friend group</b></div></div><div className="auth-decoration auth-decoration-one" /><div className="auth-decoration auth-decoration-two" /></div><section className="auth-panel"><div className="auth-card"><div className="auth-eyebrow">YOUR CONSISTENCY CLUB</div><h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p className="muted">{mode === 'login' ? 'Sign in to pick up where you left off.' : 'Join your friend group and start earning EXP.'}</p>{error && <div className="error-banner auth-error">{error}</div>}<form method="post" onSubmit={onSubmit} className="auth-form"><label>Username<input name="username" autoComplete="username" minLength={3} maxLength={40} required placeholder="e.g. fitbuddy" /></label>{mode === 'register' && <label>Display name<input name="display_name" autoComplete="name" maxLength={80} required placeholder="How your friends see you" /></label>}<label>Password<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 8 : 1} maxLength={72} required placeholder="At least 8 characters" /></label><button className="primary-button auth-submit" disabled={busy}>{busy ? <LoaderCircle size={17} className="spin" /> : null}{mode === 'login' ? 'Sign in' : 'Create account'}<ChevronRight size={17} /></button></form><p className="auth-switch">{mode === 'login' ? 'New to OneMoreRep?' : 'Already have an account?'} <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p><div className="auth-private"><ShieldCheck size={15} /> Your activities and screenshots are shared only when you choose.</div></div></section></main>;
}

function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow:string; title:string; subtitle:string; action?:ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

function MetricCard({ icon:Icon, label, value, note, tone='navy' }: { icon:typeof Activity; label:string; value:string|number; note:string; tone?:string }) {
  return <div className="metric-card"><span className={`metric-icon ${tone}`}><Icon size={19} /></span><span className="metric-label">{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

function DashboardView({ data, workouts, posts, friendRequests, userId, onDeletePost, onRespondFriend, onNavigate }: { data:Dashboard|null; workouts:Workout[]; posts:FeedPost[]; friendRequests:FriendRequest[]; userId:number; onDeletePost:(id:number)=>void; onRespondFriend:(id:number,accept:boolean)=>Promise<void>; onNavigate:(v:View)=>void }) {
  const current = data?.streak?.current_streak ?? 0;
  return <><PageHeading eyebrow="YOUR PROGRESS" title={`Good to see you${data?.name ? `, ${data.name.split(' ')[0]}` : ''}.`} subtitle="A little consistency adds up. Here’s how you’re doing." action={<button className="primary-button" onClick={() => onNavigate('activity')}><Plus size={17} /> Log activity</button>} />
    <section className="metric-grid"><MetricCard icon={Flame} label="Current streak" value={`${current} days`} note={`Personal best · ${data?.streak?.longest_streak ?? 0} days`} tone="orange" /><MetricCard icon={Sparkles} label="Total EXP" value={(data?.total ?? 0).toLocaleString()} note="Every qualifying session counts" tone="green" /><MetricCard icon={Trophy} label="Today’s EXP" value={`${data?.today ?? 0} / 50`} note="Daily cap · 30 morning + 20 evening" /><MetricCard icon={Users} label="Friends rank" value={data?.rank ? `#${data.rank}` : '—'} note="Among all your friends" tone="blue" /></section>
    {friendRequests.length>0&&<DashboardFriendRequests requests={friendRequests} onRespond={onRespondFriend} onViewFriends={()=>onNavigate('friends')}/>}
    <div className="dashboard-grid"><section className="panel today-panel"><div className="panel-heading"><div><span className="panel-kicker">TODAY</span><h2>Your daily check-in</h2></div><span className="date-chip">{new Date().toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})}</span></div><PeriodStatus icon="🌅" label="Morning" points={30} amount={data?.morning ?? 0} duration={data?.morning_duration ?? 0} /><PeriodStatus icon="🌆" label="Evening" points={20} amount={data?.evening ?? 0} duration={data?.evening_duration ?? 0} /><div className="daily-footnote"><ShieldCheck size={15} /> One qualifying session per period · 50 EXP maximum per day</div></section>
      <section className="panel activity-panel"><div className="panel-heading"><div><span className="panel-kicker">RECENT WORK</span><h2>Latest activity</h2></div><button className="text-button" onClick={() => onNavigate('history')}>View history <ChevronRight size={15} /></button></div>{workouts.slice(0,4).map((w)=><WorkoutRow key={w.id} workout={w} />)}{!workouts.length && <EmptyState icon={Activity} title="Your story starts here" text="Log your first activity to start building momentum." action="Log activity" onClick={()=>onNavigate('activity')} />}</section></div>
    <section className="panel mini-feed"><div className="panel-heading"><div><span className="panel-kicker">YOUR GROUP</span><h2>Friends feed</h2></div><button className="text-button" onClick={()=>onNavigate('feed')}>Open feed <ChevronRight size={15} /></button></div>{posts.length ? <div className="mini-feed-list">{posts.map(p=><FeedCard key={p.id} post={p} currentUserId={userId} onDeletePost={onDeletePost} />)}</div> : <div className="friend-empty"><Users size={20}/><span>Your friends’ shared workouts will show here.</span><button className="text-button" onClick={()=>onNavigate('friends')}>Find friends <ChevronRight size={15}/></button></div>}</section>
  </>;
}

function DashboardFriendRequests({requests,onRespond,onViewFriends}:{requests:FriendRequest[];onRespond:(id:number,accept:boolean)=>Promise<void>;onViewFriends:()=>void}) {
  const [busyId,setBusyId]=useState<number|null>(null);
  async function respond(id:number,accept:boolean) {
    setBusyId(id);
    try { await onRespond(id,accept); }
    finally { setBusyId(null); }
  }
  return <section className="panel request-panel dashboard-requests"><div className="panel-heading"><div><span className="panel-kicker">YOUR CIRCLE</span><h2>Friend requests <span className="count-pill">{requests.length}</span></h2></div><button className="text-button" onClick={onViewFriends}>View friends <ChevronRight size={15}/></button></div><div className="friend-list">{requests.map(request=><div className="friend-row request-row" key={request.id}><span className="avatar">{initials(request.display_name)}</span><div><b>{request.display_name}</b><small>@{request.username}</small></div><div className="request-actions"><button className="accept-button" disabled={busyId!==null} aria-label={`Accept ${request.display_name}`} onClick={()=>void respond(request.id,true)}><Check size={15}/></button><button className="decline-button" disabled={busyId!==null} aria-label={`Decline ${request.display_name}`} onClick={()=>void respond(request.id,false)}><X size={15}/></button></div></div>)}</div></section>;
}

function PeriodStatus({ icon, label, points, amount, duration }: { icon:string; label:string; points:number; amount:number; duration:number }) {
  const complete=amount>0;
  const hour=new Date().getHours();
  const notStarted=!complete&&(label==='Morning'?hour<5:hour<17);
  const summary=complete?`${durationLabel(duration)} · +${amount} EXP earned`:duration>0?`${durationLabel(duration)} logged · no EXP earned`:'No activity logged yet';
  return <div className="period-row"><span className="period-emoji">{icon}</span><div className="period-copy"><b>{label}</b><small>{notStarted?'This period has not started':summary}</small></div><span className={`period-status ${complete?'complete':''}`}>{complete ? <><Check size={14}/> +{points} EXP</> : notStarted?'Not started':'Not completed'}</span></div>;
}

function WorkoutRow({ workout }: { workout:Workout }) {
  const isStrength=workout.workout_type==='Strength';
  const icon=isStrength?<Dumbbell size={17}/>:workout.workout_type==='Walking'?<Footprints size={17}/>:<Activity size={17}/>;
  return <div className="workout-row"><span className={`workout-kind ${isStrength?'kind-strength':'kind-walk'}`}>{icon}</span><div className="workout-copy"><b>{workout.workout_type}</b><small>{niceDate(workout.workout_date)} · {workout.start_time?.slice(0,5) || '—'}{workout.has_image?' · Photo attached':''}</small></div><span className="workout-duration">{durationLabel(workout.duration)}</span><span className={`xp-chip ${workout.exp_amount?'xp-earned':''}`}>{workout.exp_amount?`+${workout.exp_amount} EXP`:'0 EXP'}</span></div>;
}

function EmptyState({ icon:Icon, title, text, action, onClick }: { icon:typeof Activity; title:string; text:string; action?:string; onClick?:()=>void }) {
  return <div className="empty-state"><span><Icon size={21}/></span><b>{title}</b><p>{text}</p>{action&&<button className="secondary-button" onClick={onClick}>{action}</button>}</div>;
}

function FeedView({ posts, workouts, achievements, userId, onDeletePost, onShare }: { posts:FeedPost[]; workouts:Workout[]; achievements:Achievement[]; userId:number; onDeletePost:(id:number)=>void; onShare:(form:FormData)=>Promise<number> }) {
  const [caption,setCaption]=useState(''); const [workoutId,setWorkoutId]=useState(''); const [achievementId,setAchievementId]=useState('');
  const [includeWorkoutImage,setIncludeWorkoutImage]=useState(false); const [file,setFile]=useState<File|null>(null);
  const [sending,setSending]=useState(false); const [error,setError]=useState(''); const [sent,setSent]=useState(false);
  const chosenWorkout=workouts.find(w=>String(w.id)===workoutId);
  async function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); setSent(false);
    if (!workoutId&&!achievementId&&!file) { setError('Choose a workout, achievement, or screenshot before sharing.'); return; }
    setSending(true);
    try {
      const body=new FormData(); body.set('caption',caption);
      if(workoutId) body.set('workout_id',workoutId);
      if(achievementId) body.set('achievement_id',achievementId);
      body.set('include_workout_image',String(includeWorkoutImage));
      if(file) body.set('screenshot',await prepareImage(file));
      await onShare(body); setCaption(''); setWorkoutId(''); setAchievementId(''); setIncludeWorkoutImage(false); setFile(null); setSent(true);
    }
    catch(err) {setError(err instanceof Error?err.message:'Could not share this post.');}
    finally {setSending(false);}
  }
  return <><PageHeading eyebrow="YOUR FRIEND GROUP" title="Friends feed" subtitle="A private space to share the work, cheer each other on, and keep showing up." action={<span className="private-pill large"><ShieldCheck size={15}/> Accepted friends only</span>} />
    <div className="feed-layout"><div className="feed-stream"><section className="panel composer"><div className="composer-title"><span className="composer-avatar"><Camera size={18}/></span><div><b>Share a moment</b><small>Only your accepted friends can see it.</small></div></div>{error&&<div className="form-error">{error}</div>}{sent&&<div className="form-success"><Check size={15}/> Shared with your friends.</div>}<form onSubmit={submit}><textarea value={caption} onChange={e=>setCaption(e.target.value)} maxLength={500} placeholder="What are you proud of today?" rows={3}/><div className="composer-controls"><div className="composer-tools"><label className="attach-button"><ImagePlus size={16}/><span>{file?file.name:'Add screenshot (max 2 MB)'}</span><input type="file" accept="image/png,image/jpeg,image/webp" disabled={includeWorkoutImage} onChange={e=>{setFile(e.target.files?.[0]||null);setIncludeWorkoutImage(false);}}/></label><select value={workoutId} onChange={e=>{setWorkoutId(e.target.value);setIncludeWorkoutImage(false);}} aria-label="Choose a workout to share"><option value="">Attach a workout</option>{workouts.map(w=><option value={w.id} key={w.id}>#{w.id} · {w.workout_type} · {niceDate(w.workout_date)}</option>)}</select><select value={achievementId} onChange={e=>setAchievementId(e.target.value)} aria-label="Choose an achievement to share"><option value="">Share an achievement</option>{achievements.map(a=><option value={a.id} key={`${a.id}-${a.badge_name}`}>{a.badge_name}</option>)}</select></div><button className="primary-button" disabled={sending}>{sending?<LoaderCircle size={16} className="spin"/>:<Send size={15}/>} Share</button></div>{chosenWorkout?.has_image&&<label className="include-image-option"><input type="checkbox" checked={includeWorkoutImage} onChange={e=>setIncludeWorkoutImage(e.target.checked)} disabled={Boolean(file)}/> Include this workout’s saved photo</label>}{file&&<div className="file-chip"><Camera size={14}/>{file.name}<button type="button" onClick={()=>{setFile(null);setIncludeWorkoutImage(false);}} aria-label="Remove screenshot"><X size={14}/></button></div>}</form></section>
      {posts.map(post=><FeedCard post={post} currentUserId={userId} onDeletePost={onDeletePost} key={post.id}/>)}{!posts.length&&<section className="panel"><EmptyState icon={Users} title="The feed is ready for your group" text="When you or a friend share a workout or screenshot, it’ll appear here." /></section>}
    </div><aside className="feed-aside"><section className="group-card"><div className="group-art"><Users size={25}/><span className="group-art-dot"/></div><span className="panel-kicker">YOUR PRIVATE SPACE</span><h3>Friends keep you going.</h3><p>Posts are visible to you and your accepted friends. Workouts never appear here unless someone chooses to share them.</p><div className="group-rule"><ShieldCheck size={16}/> Friends-only feed</div></section><section className="panel feed-tip"><span className="tip-icon"><Sparkles size={17}/></span><b>Celebrate consistency</b><p>Share an activity from your history, or add a screenshot from another workout app.</p></section></aside></div></>;
}

function FeedCard({ post, currentUserId, onDeletePost }: { post:FeedPost; currentUserId:number; onDeletePost:(id:number)=>void }) {
  const exp=post.exp_amount??0; const [liked,setLiked]=useState(post.liked_by_me); const [likes,setLikes]=useState(post.likes_count);
  const [commentsOpen,setCommentsOpen]=useState(false); const [comments,setComments]=useState<FeedComment[]>([]);
  const [commentsCount,setCommentsCount]=useState(post.comments_count); const [commentText,setCommentText]=useState('');
  const [busy,setBusy]=useState(false); const [error,setError]=useState('');
  async function toggleLike(){setBusy(true);setError('');try{const result=liked?await api.unlike(post.id):await api.like(post.id);setLiked(result.liked);setLikes(result.likes_count);}catch(e){setError(e instanceof Error?e.message:'Could not update like.');}finally{setBusy(false);}}
  async function showComments(){const open=!commentsOpen;setCommentsOpen(open);setError('');if(open){try{setComments(await api.comments(post.id));}catch(e){setError(e instanceof Error?e.message:'Could not load comments.');}}}
  async function submitComment(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!commentText.trim())return;setBusy(true);setError('');try{await api.addComment(post.id,commentText);setCommentText('');setCommentsCount(n=>n+1);setComments(await api.comments(post.id));}catch(e){setError(e instanceof Error?e.message:'Could not add comment.');}finally{setBusy(false);}}
  async function removeComment(comment:FeedComment){if(!window.confirm('Delete your comment?'))return;setBusy(true);setError('');try{await api.deleteComment(post.id,comment.id);setComments(previous=>previous.filter(item=>item.id!==comment.id));setCommentsCount(count=>Math.max(0,count-1));}catch(e){setError(e instanceof Error?e.message:'Could not delete your comment.');}finally{setBusy(false);}}
  const icon=post.workout_type==='Walking'?<Footprints size={17}/>:post.workout_type==='Sports'?<Activity size={17}/>:<Dumbbell size={17}/>;
  return <article className="panel feed-card"><div className="feed-author"><span className="avatar">{initials(post.display_name)}</span><div><b>{post.display_name}</b><small>{new Date(post.created_at).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}</small></div><span className="friends-only-tag"><ShieldCheck size={13}/> Friends</span>{post.user_id===currentUserId&&<button className="danger-button small-button user-delete-button" onClick={()=>onDeletePost(post.id)} aria-label="Delete your post"><Trash2 size={14}/> Delete</button>}</div>{post.caption&&<p className="feed-caption">{post.caption}</p>}{post.workout_id&&<div className="shared-workout"><span className="workout-kind kind-strength">{icon}</span><div className="shared-workout-copy"><span className="panel-kicker">WORKOUT SHARED</span><b>{post.workout_type} · {durationLabel(post.duration)}</b><small>{niceDate(post.workout_date)}{exp?` · +${exp} EXP earned`:''}</small></div><span className="shared-check"><Check size={15}/></span></div>}{post.achievement_name&&<div className="shared-achievement"><span><Trophy size={18}/></span><div><small>ACHIEVEMENT SHARED</small><b>{post.achievement_name}</b></div></div>}{post.image_url&&<div className="feed-image-wrap"><Image src={`${API_BASE}${post.image_url}`} alt={`Workout image shared by ${post.display_name}`} className="feed-image" width={1200} height={900} unoptimized/></div>}<div className="feed-actions"><button className={`feed-action ${liked?'feed-action-liked':''}`} onClick={()=>void toggleLike()} disabled={busy}><Heart size={16} fill={liked?'currentColor':'none'}/><span>{likes} {likes===1?'like':'likes'}</span></button><button className="feed-action" onClick={()=>void showComments()}><Activity size={16}/><span>{commentsCount} comments</span></button><span className="feed-privacy-note"><ShieldCheck size={14}/> Friends only</span></div>{error&&<div className="form-error">{error}</div>}{commentsOpen&&<section className="comments-panel">{comments.map(comment=><div className="comment-row" key={comment.id}><span className="avatar avatar-small">{initials(comment.display_name)}</span><div><b>{comment.display_name}</b><p>{comment.body}</p><small>{new Date(comment.created_at).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}</small></div>{comment.user_id===currentUserId&&<button className="icon-button comment-delete-button" onClick={()=>void removeComment(comment)} disabled={busy} aria-label="Delete your comment" title="Delete your comment"><Trash2 size={14}/></button>}</div>)}{!comments.length&&<p className="empty-inline">No comments yet. Start the conversation.</p>}<form onSubmit={submitComment} className="comment-form"><input value={commentText} onChange={e=>setCommentText(e.target.value)} maxLength={500} placeholder="Write a comment…"/><button className="secondary-button small-button" disabled={busy||!commentText.trim()}>Comment</button></form></section>}</article>;
}

function ActivityView({ onSave }: { onSave:(payload:unknown, photo?:File|null)=>Promise<void> }) {
  const [kind,setKind]=useState<'Strength'|'Walking'|'Sports'>('Strength'); const [day,setDay]=useState(todayString()); const [start,setStart]=useState('07:00'); const [end,setEnd]=useState('07:40'); const [notes,setNotes]=useState(''); const [rows,setRows]=useState<Exercise[]>([{exercise_name:'',weight:'',reps:'',sets:''}]); const [walking,setWalking]=useState({distance:'',steps:'',calories:'',avg_speed:''}); const [sport,setSport]=useState(''); const [photo,setPhoto]=useState<File|null>(null); const [saving,setSaving]=useState(false); const [error,setError]=useState(''); const [saved,setSaved]=useState(false);
  const duration=useMemo(()=>{if(!start||!end)return 0; const [sh,sm]=start.split(':').map(Number);const [eh,em]=end.split(':').map(Number);return Math.max(0,eh*60+em-sh*60-sm);},[start,end]);
  function changeRow(i:number,key:keyof Exercise,value:string){setRows(old=>old.map((row,index)=>index===i?{...row,[key]:value}:row));}
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setError('');setSaved(false);setSaving(true);try{const payload=kind==='Strength'?{kind,activity_date:day,start_time:start,end_time:end,notes,exercises:rows.map(r=>({exercise_name:r.exercise_name.trim(),weight:Number(r.weight),reps:Number(r.reps),sets:Number(r.sets)}))}:kind==='Walking'?{kind,activity_date:day,start_time:start,end_time:end,notes,walking:{distance:Number(walking.distance),steps:Number(walking.steps),calories:Number(walking.calories),avg_speed:Number(walking.avg_speed)}}:{kind,activity_date:day,start_time:start,end_time:end,notes,sport:{sport_name:sport.trim()}};await onSave(payload,photo?await prepareImage(photo):null);setSaved(true);setRows([{exercise_name:'',weight:'',reps:'',sets:''}]);setNotes('');setPhoto(null);setSport('');}catch(err){setError(err instanceof Error?err.message:'Could not save this activity.');}finally{setSaving(false);}}
  return <><PageHeading eyebrow="LOG YOUR MOVEMENT" title="New activity" subtitle="Record what you did. Your duration is calculated from the start and end times."/><section className="panel activity-form-panel"><div className="activity-type-switch"><button className={kind==='Strength'?'type-active':''} onClick={()=>setKind('Strength')} type="button"><Dumbbell size={17}/> Strength</button><button className={kind==='Walking'?'type-active':''} onClick={()=>setKind('Walking')} type="button"><Footprints size={17}/> Walking</button><button className={kind==='Sports'?'type-active':''} onClick={()=>setKind('Sports')} type="button"><Activity size={17}/> Sports</button></div>{error&&<div className="form-error">{error}</div>}{saved&&<div className="form-success"><Check size={15}/> Activity saved to your private history. Share it with friends from the feed when you’re ready.</div>}<form onSubmit={submit} className="activity-form"><div className="form-grid form-grid-three"><label>Date<input type="date" value={day} onChange={e=>setDay(e.target.value)} required/></label><label>Start time<input type="time" value={start} onChange={e=>setStart(e.target.value)} required/></label><label>End time<input type="time" value={end} onChange={e=>setEnd(e.target.value)} required/></label></div><div className="duration-preview"><Clock3 size={17}/><span>Calculated duration</span><strong>{duration ? `${duration} min` : 'Set an end time after start'}</strong></div>
    {kind==='Strength'?<div className="exercise-section"><div className="section-row"><div><b>Exercises</b><small>Add one row for each exercise.</small></div><button className="secondary-button small-button" type="button" onClick={()=>setRows(old=>[...old,{exercise_name:'',weight:'',reps:'',sets:''}])}><Plus size={15}/> Add exercise</button></div>{rows.map((row,i)=><div className="exercise-row" key={i}><label className="exercise-name">Exercise<input value={row.exercise_name} onChange={e=>changeRow(i,'exercise_name',e.target.value)} placeholder="e.g. Bench press" required/></label><label>Weight (kg)<input type="number" min="0" step="0.1" value={row.weight} onChange={e=>changeRow(i,'weight',e.target.value)} required/></label><label>Reps<input type="number" min="1" value={row.reps} onChange={e=>changeRow(i,'reps',e.target.value)} required/></label><label>Sets<input type="number" min="1" value={row.sets} onChange={e=>changeRow(i,'sets',e.target.value)} required/></label>{rows.length>1&&<button className="remove-row" type="button" aria-label="Remove exercise" onClick={()=>setRows(old=>old.filter((_,idx)=>idx!==i))}><X size={16}/></button>}</div>)}</div>:kind==='Walking'?<div className="form-grid form-grid-four walking-fields"><label>Distance (km)<input type="number" min="0" step="0.01" value={walking.distance} onChange={e=>setWalking({...walking,distance:e.target.value})} required/></label><label>Steps<input type="number" min="0" value={walking.steps} onChange={e=>setWalking({...walking,steps:e.target.value})} required/></label><label>Calories<input type="number" min="0" step="1" value={walking.calories} onChange={e=>setWalking({...walking,calories:e.target.value})} required/></label><label>Avg. speed (km/h)<input type="number" min="0" step="0.1" value={walking.avg_speed} onChange={e=>setWalking({...walking,avg_speed:e.target.value})} required/></label></div>:<label>Sport<input value={sport} onChange={e=>setSport(e.target.value)} maxLength={80} placeholder="e.g. Basketball, football, swimming" required/></label>}
    <label>Notes <span className="optional">Optional</span><textarea value={notes} onChange={e=>setNotes(e.target.value)} maxLength={1000} rows={3} placeholder="Add a note for your own history"/></label><label className="attach-button activity-photo"><Camera size={16}/><span>{photo?photo.name:'Workout photo · auto-compressed to 2 MB'}</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setPhoto(e.target.files?.[0]||null)}/></label><div className="form-bottom"><p><ShieldCheck size={15}/> Your activity and photo stay private unless you share them.</p><button className="primary-button" disabled={saving||duration<=0}>{saving?<LoaderCircle size={16} className="spin"/>:<Check size={16}/>} Save activity</button></div></form></section></>;
}

function ProgressView({reports,onSave,onDelete}:{reports:ProgressReport[];onSave:(form:FormData)=>Promise<void>;onDelete:(id:number)=>void}) {
 const [day,setDay]=useState(todayString());const [notes,setNotes]=useState('');const [photo,setPhoto]=useState<File|null>(null);const [saving,setSaving]=useState(false);const [error,setError]=useState('');const [saved,setSaved]=useState(false);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setSaving(true);setError('');setSaved(false);const form=new FormData();form.set('report_date',day);form.set('notes',notes);try{if(photo)form.set('photo',await prepareImage(photo));await onSave(form);setSaved(true);setNotes('');setPhoto(null);}catch(err){setError(err instanceof Error?err.message:'Could not save report.');}finally{setSaving(false);}}
 return <><PageHeading eyebrow="PERSONAL CHECK-INS" title="Progress reports" subtitle="Keep a private record of how you feel and add a fitness photo when you want."/><div className="progress-layout"><section className="panel progress-form"><div className="panel-heading"><div><span className="panel-kicker">DAILY REPORT</span><h2>Log your progress</h2></div><Activity className="heading-icon" size={20}/></div>{error&&<div className="form-error">{error}</div>}{saved&&<div className="form-success"><Check size={15}/> Progress report saved.</div>}<form className="activity-form" onSubmit={submit}><label>Date<input type="date" value={day} onChange={e=>setDay(e.target.value)} required/></label><label>Notes <span className="optional">Optional</span><textarea rows={3} maxLength={1000} value={notes} onChange={e=>setNotes(e.target.value)} placeholder="How are you feeling?"/></label><label className="attach-button activity-photo"><Camera size={16}/><span>{photo?photo.name:'Progress photo · auto-compressed to 2 MB'}</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setPhoto(e.target.files?.[0]||null)}/></label><button className="primary-button" disabled={saving}>{saving?<LoaderCircle size={16} className="spin"/>:<Check size={16}/>} Save report</button></form></section><section className="progress-history"><div className="panel-heading"><div><span className="panel-kicker">PRIVATE HISTORY</span><h2>{reports.length} check-ins</h2></div></div>{reports.map(r=><article className="panel progress-card" key={r.id}><div className="progress-date"><b>{niceDate(r.report_date)}</b><button className="danger-button small-button user-delete-button" onClick={()=>onDelete(r.id)}><Trash2 size={14}/> Delete</button></div>{r.notes&&<p>{r.notes}</p>}{r.image_url&&<Image src={`${API_BASE}${r.image_url}`} alt={`Progress photo for ${niceDate(r.report_date)}`} className="progress-image" width={1000} height={700} unoptimized/>}</article>)}{!reports.length&&<section className="panel"><EmptyState icon={Activity} title="Your check-ins will appear here" text="Add a private note or optional fitness photo to start your progress history."/></section>}</section></div></>;
}

function FriendsView({ data, groups, onReload, onGroupsReload, onNotice }: { data:FriendList|null; groups:FriendGroup[]; onReload:()=>void; onGroupsReload:()=>void; onNotice:(message:string)=>void }) {
  const [username,setUsername]=useState('');const [loading,setLoading]=useState(false);const [error,setError]=useState('');
  async function add(e:FormEvent<HTMLFormElement>){e.preventDefault();setLoading(true);setError('');try{await api.addFriend(username);setUsername('');onNotice('Friend request sent.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not send the request.');}finally{setLoading(false);}}
  async function respond(id:number,accept:boolean){setLoading(true);setError('');try{await api.respondFriend(id,accept);onNotice(accept?'Friend request accepted.':'Friend request declined.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not update the request.');}finally{setLoading(false);}}
  return <><PageHeading eyebrow="YOUR PRIVATE GROUP" title="Friends" subtitle="Connect with people you know. Only accepted friends can see each other’s feed posts."/><div className="friends-grid"><section className="panel friends-main"><div className="panel-heading"><div><span className="panel-kicker">ACCEPTED FRIENDS</span><h2>Your circle <span className="count-pill">{data?.friends.length??0}</span></h2></div><Users size={21} className="heading-icon"/></div>{data?.friends.length?<div className="friend-list">{data.friends.map(f=><div className="friend-row" key={f.username}><span className="avatar">{initials(f.display_name)}</span><div><b>{f.display_name}</b><small>@{f.username}</small></div><span className="friend-badge"><Check size={13}/> Friend</span></div>)}</div>:<EmptyState icon={Users} title="Your circle is waiting" text="Send a request to a friend to start your private group."/>}</section>
    <div className="friends-side"><section className="panel add-friend-card"><span className="panel-kicker">GROW YOUR CIRCLE</span><h2>Add a friend</h2><p>Send a request using their OneMoreRep username.</p>{error&&<div className="form-error">{error}</div>}<form onSubmit={add} className="add-friend-form"><input value={username} onChange={e=>setUsername(e.target.value)} placeholder="Friend’s username" minLength={1} required/><button className="primary-button" disabled={loading}>{loading?<LoaderCircle size={16} className="spin"/>:<UserPlus size={16}/>} Send request</button></form></section>
    <section className="panel request-panel"><div className="panel-heading"><div><span className="panel-kicker">PENDING</span><h2>Incoming requests</h2></div><span className="count-pill">{data?.incoming.length??0}</span></div>{data?.incoming.length?data.incoming.map(req=><div className="friend-row request-row" key={req.id}><span className="avatar">{initials(req.display_name)}</span><div><b>{req.display_name}</b><small>@{req.username}</small></div><div className="request-actions"><button className="accept-button" disabled={loading} aria-label={`Accept ${req.display_name}`} onClick={()=>respond(req.id,true)}><Check size={15}/></button><button className="decline-button" disabled={loading} aria-label={`Decline ${req.display_name}`} onClick={()=>respond(req.id,false)}><X size={15}/></button></div></div>):<p className="empty-inline">No incoming requests.</p>}{data?.outgoing.map(friend=><div className="outgoing-row" key={friend.username}><span>{friend.display_name}</span><small>Request pending</small></div>)}</section></div></div><FriendGroupsPanel friends={data?.friends??[]} groups={groups} onReload={onGroupsReload} onNotice={onNotice}/></>;
}

function FriendGroupsPanel({friends,groups,onReload,onNotice}:{friends:Friend[];groups:FriendGroup[];onReload:()=>void;onNotice:(message:string)=>void}){
 const [name,setName]=useState('');const [selected,setSelected]=useState<Record<number,string>>({});const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 async function create(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');try{await api.createGroup(name);setName('');onNotice('Friend group created.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not create group.');}finally{setBusy(false);}}
 async function add(groupId:number){setBusy(true);setError('');try{await api.addGroupMember(groupId,selected[groupId]||'');setSelected(old=>({...old,[groupId]:''}));onNotice('Friend added to group.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not add group member.');}finally{setBusy(false);}}
 async function remove(groupId:number,memberId:number){setBusy(true);setError('');try{await api.removeGroupMember(groupId,memberId);onNotice('Group membership updated.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not update group membership.');}finally{setBusy(false);}}
 async function discard(groupId:number){if(!window.confirm('Delete this friend group? Its members will remain friends.'))return;setBusy(true);setError('');try{await api.deleteGroup(groupId);onNotice('Friend group deleted.');onReload();}catch(err){setError(err instanceof Error?err.message:'Could not delete group.');}finally{setBusy(false);}}
 return <section className="panel friend-groups-panel"><div className="panel-heading"><div><span className="panel-kicker">YOUR CIRCLES</span><h2>Friend groups</h2></div><Users size={20} className="heading-icon"/></div><p className="muted">Make smaller circles for teams, training partners, or shared goals. Groups only include people who are already your friends.</p>{error&&<div className="form-error">{error}</div>}<form className="group-create-form" onSubmit={create}><input value={name} onChange={e=>setName(e.target.value)} maxLength={60} placeholder="Group name, e.g. Football" required/><button className="primary-button" disabled={busy}><Plus size={15}/> Create group</button></form>{groups.length?<div className="friend-groups-list">{groups.map(group=><article className="friend-group-card" key={group.id}><div className="panel-heading"><div><span className="panel-kicker">{group.is_owner?'GROUP OWNER':'MEMBER'}</span><h3>{group.name} <span className="count-pill">{group.members.length}</span></h3></div>{group.is_owner&&<button className="danger-button small-button" disabled={busy} onClick={()=>void discard(group.id)}>Delete group</button>}</div><div className="friend-group-members">{group.members.map(member=><div className="friend-row" key={member.id}><span className="avatar">{initials(member.display_name||'Friend')}</span><div><b>{member.display_name||'Friend'}</b>{member.username&&<small>@{member.username}</small>}</div>{member.id!==group.owner_id&&(group.is_owner||member.is_me)&&<button className="danger-button small-button" disabled={busy} onClick={()=>void remove(group.id,member.id)}>{member.is_me?'Leave group':'Remove'}</button>}</div>)}</div>{group.is_owner&&friends.length>0&&<form className="group-create-form" onSubmit={e=>{e.preventDefault();void add(group.id);}}><select aria-label={`Add a friend to ${group.name}`} value={selected[group.id]||''} onChange={e=>setSelected(old=>({...old,[group.id]:e.target.value}))} required><option value="">Choose a friend</option>{friends.filter(friend=>!group.members.some(member=>member.username===friend.username)).map(friend=><option value={friend.username} key={friend.username}>{friend.display_name}</option>)}</select><button className="secondary-button" disabled={busy||!selected[group.id]}><UserPlus size={15}/> Add member</button></form>}</article>)}</div>:<p className="empty-inline">Create a group to organize friends into circles.</p>}</section>;
}

function HistoryView({ rows, onShare, onDelete, onDetails }: { rows:Workout[]; onShare:()=>void; onDelete:(id:number)=>void; onDetails:(id:number)=>Promise<WorkoutDetail> }) {
  const [selected,setSelected]=useState<WorkoutDetail|null>(null);
  const [selectedId,setSelectedId]=useState<number|null>(null);
  const [detailError,setDetailError]=useState('');
  async function showDetails(id:number) {
    setDetailError('');
    try { setSelected(await onDetails(id)); setSelectedId(id); }
    catch(e) { setDetailError(e instanceof Error?e.message:'Could not load activity details.'); }
  }
  return <><PageHeading eyebrow="YOUR ACTIVITY" title="Workout history" subtitle="Every session you log stays here, whether or not you share it." action={<button className="secondary-button" onClick={onShare}><Users size={16}/> Share with friends</button>}/><section className="panel table-panel"><div className="panel-heading"><div><span className="panel-kicker">ALL SESSIONS</span><h2>{rows.length} activities</h2></div></div>{detailError&&<div className="form-error">{detailError}</div>}{rows.length?<div className="responsive-table"><table><thead><tr><th>Date</th><th>Activity</th><th>Start</th><th>Duration</th><th>EXP</th><th></th></tr></thead><tbody>{rows.map(w=><tr key={w.id}><td>{niceDate(w.workout_date)}</td><td><button className="table-kind detail-trigger" onClick={()=>void showDetails(w.id)} aria-label={`View ${w.workout_type} details`}>{w.workout_type==='Walking'?<Footprints size={15}/>:w.workout_type==='Sports'?<Activity size={15}/>:<Dumbbell size={15}/>} {w.workout_type}<ChevronRight size={13}/></button></td><td>{w.start_time?.slice(0,5)||'—'}</td><td>{durationLabel(w.duration)}</td><td><span className={`xp-chip ${w.exp_amount?'xp-earned':''}`}>{w.exp_amount?`+${w.exp_amount}`:'0'} EXP</span></td><td><button className="danger-button small-button user-delete-button" onClick={()=>onDelete(w.id)} aria-label="Delete your workout"><Trash2 size={14}/> Delete</button></td></tr>)}</tbody></table></div>:<EmptyState icon={Activity} title="No activities yet" text="Your logged workouts will appear here."/>}
    {selected&&<section className="activity-detail"><div className="panel-heading"><div><span className="panel-kicker">ACTIVITY DETAILS · #{selectedId}</span><h2>{selected.workout_type}</h2></div><button className="icon-button" onClick={()=>setSelected(null)} aria-label="Close activity details"><X size={17}/></button></div>{selected.workout_type==='Strength'?<div className="responsive-table"><table><thead><tr><th>Exercise</th><th>Weight</th><th>Reps</th><th>Sets</th></tr></thead><tbody>{selected.details.map((item,index)=><tr key={index}><td>{item.exercise_name}</td><td>{item.weight} kg</td><td>{item.reps}</td><td>{item.sets}</td></tr>)}</tbody></table></div>:<div className="detail-facts">{Object.entries(selected.details[0]??{}).map(([key,value])=><div key={key}><small>{key.replace('_',' ')}</small><b>{value}</b></div>)}</div>}</section>}
  </section></>;
}

function ExpView({ rows }: { rows:ExpRecord[] }) {
  return <><PageHeading eyebrow="CONSISTENCY REWARDS" title="EXP history" subtitle="Workout rewards and any administrator adjustments to your balance."/><section className="panel table-panel"><div className="panel-heading"><div><span className="panel-kicker">EXP HISTORY</span><h2>{rows.reduce((n,r)=>n+r.exp_amount,0).toLocaleString()} total EXP</h2></div><Sparkles className="heading-icon" size={20}/></div>{rows.length?<div className="responsive-table"><table><thead><tr><th>Date</th><th>Period</th><th>Activity</th><th>Duration</th><th>EXP</th></tr></thead><tbody>{rows.map((r,i)=><tr key={`${r.activity_date}-${r.activity_period}-${i}`}><td>{niceDate(r.activity_date)}</td><td>{r.source==='admin_adjustment'?'Admin adjustment':nicePeriod(r.activity_period)}</td><td>{r.source==='admin_adjustment'?<>{r.reason}<small className="admin-username">Adjusted by @{r.admin_username}</small></>:r.workout_type}</td><td>{r.duration===null?'—':durationLabel(r.duration)}</td><td><span className={`xp-chip ${r.exp_amount>0?'xp-earned':''}`}>{r.exp_amount>0?'+':''}{r.exp_amount} EXP</span></td></tr>)}</tbody></table></div>:<EmptyState icon={Sparkles} title="Your first EXP is close" text="A session longer than 30 minutes in the morning or evening period earns EXP."/>}</section></>;
}

function LeaderboardView({ rows, groups, currentId, onSelectGroup }: { rows:LeaderboardRow[]; groups:FriendGroup[]; currentId:number; onSelectGroup:(id:number|null)=>void }) {
  const [selected,setSelected]=useState('');
  function choose(value:string){setSelected(value);onSelectGroup(value?Number(value):null);}
  const title=groups.find(group=>String(group.id)===selected)?.name||'All friends';
  return <><PageHeading eyebrow="FRIENDLY COMPETITION" title="Leaderboard" subtitle="Compare consistency with all your friends or choose one of your groups." action={<span className="private-pill"><Users size={14}/> Friends only</span>}/><section className="panel table-panel"><div className="panel-heading"><div><span className="panel-kicker">FRIENDS LEADERBOARD</span><h2>{title}</h2></div><Trophy className="heading-icon" size={21}/></div><label className="leaderboard-scope">Show standings<select aria-label="Leaderboard group" value={selected} onChange={e=>choose(e.target.value)}><option value="">All friends</option>{groups.map(group=><option key={group.id} value={group.id}>{group.name}</option>)}</select></label>{rows.length?<div className="responsive-table"><table><thead><tr><th>Rank</th><th>Member</th><th>Total EXP</th><th>This week</th><th>This month</th><th>Streak</th><th>Workouts</th></tr></thead><tbody>{rows.map((row,index)=><tr className={row.id===currentId?'current-user-row':''} key={row.id}><td><span className={`rank-mark ${index<3?'rank-top':''}`}>{index+1}</span></td><td><span className="table-person"><span className="avatar avatar-small">{initials(row.display_name)}</span><b>{row.display_name}{row.id===currentId?' (you)':''}</b></span></td><td><b>{row.total_exp.toLocaleString()}</b></td><td>{row.weekly_exp}</td><td>{row.monthly_exp}</td><td>{row.current_streak} days <small className="muted">· best {row.longest_streak}</small></td><td>{row.total_workouts}</td></tr>)}</tbody></table></div>:<EmptyState icon={Trophy} title="No standings yet" text={selected?'Group members will appear here as they log activity.':'Add friends to see your private leaderboard.'}/>}</section></>;
}

function StatisticsView({ data }: { data:Statistics|null }) {
  const items=[['Total EXP',data?.total_exp??0,Sparkles],['Total workouts',data?.total_workouts??0,Activity],['Strength workouts',data?.strength_workouts??0,Dumbbell],['Walking sessions',data?.walking_sessions??0,Footprints],['Sports sessions',data?.sports_sessions??0,Activity],['Weight lifted',`${Number(data?.total_weight??0).toLocaleString()} kg`,Award],['Walking distance',`${Number(data?.total_distance??0).toLocaleString()} km`,Footprints],['Total steps',Number(data?.total_steps??0).toLocaleString(),Activity],['Longest streak',`${data?.longest_streak??0} days`,Flame]] as const;
  return <><PageHeading eyebrow="YOUR CONSISTENCY, IN NUMBERS" title="Statistics" subtitle="Your totals come directly from your logged workouts and earned EXP."/><section className="stats-grid">{items.map(([label,value,Icon])=><MetricCard key={label} icon={Icon} label={label} value={value} note="All time" tone="blue"/>)}<MetricCard icon={Flame} label="Current streak" value={`${data?.current_streak??0} days`} note="Qualifying days in a row" tone="orange"/></section></>;
}

function ProfileView({ user, stats, achievements, onSignOut }: { user:User; stats:Statistics|null; achievements:Achievement[]; onSignOut:()=>void }) {
  return <><PageHeading eyebrow="YOUR ACCOUNT" title="Profile" subtitle="Your OneMoreRep details, personal bests, and earned badges."/><section className="panel profile-panel"><div className="profile-hero"><span className="profile-avatar">{initials(user.display_name)}</span><div><h2>{user.display_name}</h2><p>@{user.username}</p></div><span className="private-pill"><ShieldCheck size={14}/> Private account</span></div><div className="profile-facts"><div><small>Current streak</small><b>{stats?.current_streak??0} days</b></div><div><small>Longest streak</small><b>{stats?.longest_streak??0} days</b></div><div><small>Total EXP</small><b>{(stats?.total_exp??0).toLocaleString()}</b></div><div><small>Logged activities</small><b>{stats?.total_workouts??0}</b></div></div><div className="profile-privacy"><ShieldCheck size={19}/><div><b>Your posts are shared with accepted friends only.</b><p>Activities are private until you choose to share them on the friends feed.</p></div></div><section className="achievement-section"><div className="panel-heading"><div><span className="panel-kicker">MILESTONES</span><h2>Your achievements <span className="count-pill">{achievements.length}</span></h2></div><Award size={20} className="heading-icon"/></div>{achievements.length?<div className="achievement-grid">{achievements.map(item=><div className="achievement-card" key={item.badge_name}><span><Trophy size={17}/></span><div><b>{item.badge_name}</b><small>Earned {niceDate(item.earned_at)}</small></div></div>)}</div>:<p className="empty-inline">Your first badge is waiting for your next milestone.</p>}</section><button className="secondary-button logout-button" onClick={onSignOut}><LogOut size={16}/> Log out</button></section></>;
}

function AdminView({users,actorId,onLoadUser,onReloadUsers,onAdjustLeaderboard}:{users:AdminAccount[];actorId:number;onLoadUser:(id:number)=>Promise<AdminReport>;onReloadUsers:()=>Promise<AdminAccount[]>;onAdjustLeaderboard:(id:number,changes:LeaderboardChanges,reason:string)=>Promise<void>}) {
  const [selectedId,setSelectedId]=useState<number|null>(users[0]?.id??null);
  const [report,setReport]=useState<AdminReport|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  async function refresh(){if(selectedId!==null)setReport(await onLoadUser(selectedId));await onReloadUsers();}
  async function removeMember(id:number){if(!window.confirm('Permanently delete this account and all of its workouts, progress reports, posts, comments, and uploaded images? This cannot be undone.'))return;setError('');try{await api.adminDeleteMember(id);const remaining=await onReloadUsers();if(id===selectedId){setReport(null);setSelectedId(remaining[0]?.id??null);}}catch(err){setError(err instanceof Error?err.message:'Could not delete account.');}}
  useEffect(()=>{if(selectedId===null)return;let cancelled=false;Promise.resolve().then(()=>{if(cancelled)return undefined;setLoading(true);setError('');return onLoadUser(selectedId);}).then(value=>{if(!cancelled&&value)setReport(value);}).catch(err=>{if(!cancelled)setError(err instanceof Error?err.message:'Could not load account data.');}).finally(()=>{if(!cancelled)setLoading(false);});return()=>{cancelled=true;};},[selectedId,onLoadUser]);
  return <><PageHeading eyebrow="ROLE-BASED ACCESS" title="Admin console" subtitle="Review and edit member records, workout details, progress reports, and friend feed activity." action={<span className="private-pill"><ShieldCheck size={14}/> Administrator</span>}/>
    <section className="panel admin-members"><div className="panel-heading"><div><span className="panel-kicker">MEMBERS</span><h2>{users.length} accounts</h2></div></div>{users.length?<div className="responsive-table"><table><thead><tr><th>Member</th><th>Role</th><th>Total EXP</th><th>Workouts</th><th>Progress reports</th><th>Posts</th><th>Joined</th><th></th></tr></thead><tbody>{users.map(member=><tr key={member.id} className={member.id===selectedId?'current-user-row':''}><td><b>{member.display_name}</b><small className="admin-username">@{member.username}</small></td><td><span className="admin-role">{member.role}</span></td><td><b>{member.total_exp.toLocaleString()}</b></td><td>{member.workout_count}</td><td>{member.progress_count}</td><td>{member.post_count}</td><td>{niceDate(member.created_at)}</td><td className="admin-row-actions"><button className="secondary-button small-button" onClick={()=>setSelectedId(member.id)}>View data</button>{member.id!==actorId&&<button className="danger-button small-button" onClick={()=>void removeMember(member.id)}>Delete</button>}</td></tr>)}</tbody></table></div>:<EmptyState icon={Users} title="No accounts found" text="New member accounts will appear here."/>}</section>
    {error&&<div className="form-error">{error}</div>}{loading&&<div className="loading-line"><LoaderCircle size={16} className="spin"/> Loading member data…</div>}
      {report&&!loading&&<><section className="panel admin-user-summary"><span className="avatar">{initials(report.user.display_name)}</span><div><span className="panel-kicker">ACCOUNT RECORD</span><h2>{report.user.display_name} <small>@{report.user.username}</small></h2></div><span className="admin-role">{report.user.role}</span><b>{report.user.total_exp.toLocaleString()} EXP</b><span className="muted">Joined {niceDate(report.user.created_at)}</span></section>
      <AdminMemberEditor member={report.user} onSave={async(name)=>{await api.adminUpdateMember(report.user.id,name);await refresh();}} />
      <AdminLeaderboardEditor member={report.user} onSave={async(changes,reason)=>{await onAdjustLeaderboard(report.user.id,changes,reason);await refresh();}} />
      <section className="panel"><div className="panel-heading"><div><span className="panel-kicker">LEADERBOARD AUDIT</span><h2>{report.exp_adjustments.length} administrator adjustments</h2></div></div>{report.exp_adjustments.length?report.exp_adjustments.map((item,index)=><article className="admin-engagement" key={`${item.created_at}-${index}`}><div><b>{describeLeaderboardChanges(item)} · @{item.admin_username}</b><p>{item.reason}</p><small>{new Date(item.created_at).toLocaleString()}</small></div></article>):<p className="empty-inline">No leaderboard adjustments have been made.</p>}</section>
      <div className="admin-data-grid"><section className="panel"><div className="panel-heading"><div><span className="panel-kicker">WORKOUT HISTORY</span><h2>{report.workouts.length} activities</h2></div></div>{report.workouts.length?report.workouts.map(workout=><article className="admin-record" key={workout.id}><div className="progress-date"><b>{workout.workout_type}{workout.sport_name?` · ${workout.sport_name}`:''}</b><span>{niceDate(workout.workout_date)}</span></div><small>{durationLabel(workout.duration)} · {workout.start_time?.slice(0,5)}{workout.exp_amount?` · +${workout.exp_amount} EXP`:''}</small>{workout.notes&&<p>{workout.notes}</p>}<AdminWorkoutEditor workout={workout} onSave={async(payload)=>{await api.adminUpdateWorkout(report.user.id,workout.id,payload);await refresh();}}/><AdminDeleteButton label="Delete workout" onDelete={()=>api.adminDeleteWorkout(report.user.id,workout.id)} onDeleted={refresh}/>{workout.image_url&&<Image src={`${API_BASE}${workout.image_url}`} alt="Member workout attachment" className="admin-image" width={900} height={650} unoptimized/>}</article>):<p className="empty-inline">No workout records.</p>}</section>
      <section className="panel"><div className="panel-heading"><div><span className="panel-kicker">PROGRESS REPORTS</span><h2>{report.progress_reports.length} check-ins</h2></div></div>{report.progress_reports.length?report.progress_reports.map(progress=><article className="admin-record" key={progress.id}><div className="progress-date"><b>{niceDate(progress.report_date)}</b></div>{progress.notes&&<p>{progress.notes}</p>}<AdminProgressEditor report={progress} onSave={async(payload)=>{await api.adminUpdateProgress(report.user.id,progress.id,payload);await refresh();}}/><AdminDeleteButton label="Delete report" onDelete={()=>api.adminDeleteProgress(report.user.id,progress.id)} onDeleted={refresh}/>{progress.image_url&&<Image src={`${API_BASE}${progress.image_url}`} alt="Member progress attachment" className="admin-image" width={900} height={650} unoptimized/>}</article>):<p className="empty-inline">No progress reports.</p>}</section>
      <section className="panel"><div className="panel-heading"><div><span className="panel-kicker">FRIEND FEED POSTS</span><h2>{report.posts.length} posts</h2></div></div>{report.posts.length?report.posts.map(post=><article className="admin-record" key={post.id}><div className="progress-date"><b>{post.achievement_name?`Achievement · ${post.achievement_name}`:post.workout_id?`Workout · #${post.workout_id}`:'Post'}</b><span>{new Date(post.created_at).toLocaleDateString()}</span></div>{post.caption&&<p>{post.caption}</p>}<small>{post.likes_count} likes · {post.comments_count} comments</small><AdminPostEditor caption={post.caption} onSave={async(caption)=>{await api.adminUpdatePost(report.user.id,post.id,caption);await refresh();}}/><AdminDeleteButton label="Delete post" onDelete={()=>api.adminDeletePost(report.user.id,post.id)} onDeleted={refresh}/>{post.image_url&&<Image src={`${API_BASE}${post.image_url}`} alt="Member feed attachment" className="admin-image" width={900} height={650} unoptimized/>}</article>):<p className="empty-inline">No posts.</p>}</section>
      <section className="panel"><div className="panel-heading"><div><span className="panel-kicker">POST ENGAGEMENT</span><h2>{report.comments.length} comments · {report.likes.length} likes</h2></div></div>{report.comments.map(comment=><article className="admin-engagement" key={`c-${comment.id}`}><div><b>{comment.commenter} commented on post #{comment.post_id}</b><p>{comment.body}</p><small>{new Date(comment.created_at).toLocaleString()}</small></div><AdminDeleteButton label="Delete comment" onDelete={()=>api.adminDeleteComment(report.user.id,comment.id)} onDeleted={refresh}/></article>)}{report.likes.map((like,index)=><article className="admin-engagement" key={`l-${like.post_id}-${index}`}><b>{like.liker} liked post #{like.post_id}</b><small>{new Date(like.created_at).toLocaleString()}</small></article>)}{!report.comments.length&&!report.likes.length&&<p className="empty-inline">No post engagement.</p>}</section></div></>}
  </>;
}

function AdminMemberEditor({member,onSave}:{member:AdminAccount;onSave:(name:string)=>Promise<void>}){
 const [open,setOpen]=useState(false);const [name,setName]=useState(member.display_name);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');try{await onSave(name);setOpen(false);}catch(err){setError(err instanceof Error?err.message:'Could not update member.');}finally{setBusy(false);}}
 return <div className="admin-editor"><button type="button" className="secondary-button small-button" onClick={()=>{setName(member.display_name);setOpen(v=>!v);}}>Edit member name</button>{open&&<form className="admin-edit-form" onSubmit={submit}>{error&&<span className="form-error">{error}</span>}<label>Display name<input value={name} onChange={e=>setName(e.target.value)} maxLength={80} required/></label><div className="admin-edit-actions"><button className="primary-button small-button" disabled={busy}>{busy?'Saving…':'Save name'}</button><button type="button" className="secondary-button small-button" onClick={()=>setOpen(false)}>Cancel</button></div></form>}</div>;
}

function AdminLeaderboardEditor({member,onSave}:{member:AdminAccount;onSave:(changes:LeaderboardChanges,reason:string)=>Promise<void>}){
 const empty:LeaderboardChanges={amount:0,weekly_amount:0,monthly_amount:0,current_streak_delta:0,longest_streak_delta:0,workout_delta:0};
 const fields:Array<[keyof LeaderboardChanges,string]>=[['amount','Total EXP'],['weekly_amount','This week'],['monthly_amount','This month'],['current_streak_delta','Current streak (days)'],['longest_streak_delta','Best streak (days)'],['workout_delta','Workouts']];
 const [open,setOpen]=useState(false);const [changes,setChanges]=useState<LeaderboardChanges>(empty);const [reason,setReason]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();if(!Object.values(changes).some(Boolean)){setError('Enter at least one non-zero change.');return;}setBusy(true);setError('');try{await onSave(changes,reason);setChanges(empty);setReason('');setOpen(false);}catch(err){setError(err instanceof Error?err.message:'Could not adjust leaderboard values.');}finally{setBusy(false);}}
 return <div className="admin-editor"><button type="button" className="secondary-button small-button" onClick={()=>setOpen(v=>!v)}>Adjust leaderboard</button>{open&&<form className="admin-edit-form" onSubmit={submit}>{error&&<span className="form-error">{error}</span>}<p className="muted">Current values: {member.total_exp.toLocaleString()} EXP · {member.weekly_exp.toLocaleString()} this week · {member.monthly_exp.toLocaleString()} this month · {member.current_streak} day streak · {member.longest_streak} best · {member.workout_count} workouts. Enter signed changes; rank updates automatically.</p><div className="admin-edit-grid">{fields.map(([key,label])=><label key={key}>{label}<input type="number" min={key==='current_streak_delta'||key==='longest_streak_delta'?-100_000:-1_000_000} max={key==='current_streak_delta'||key==='longest_streak_delta'?100_000:1_000_000} step={1} value={changes[key]} onChange={e=>setChanges(previous=>({...previous,[key]:Number(e.target.value)}))}/></label>)}</div><p className="empty-inline">Total EXP changes also affect this week and this month. Add a separate change to those fields only if needed.</p><label>Reason<textarea value={reason} onChange={e=>setReason(e.target.value)} maxLength={250} rows={2} placeholder="Explain this adjustment" required/></label><div className="admin-edit-actions"><button className="primary-button small-button" disabled={busy}>{busy?'Saving…':'Save changes'}</button><button type="button" className="secondary-button small-button" onClick={()=>setOpen(false)}>Cancel</button></div></form>}</div>;
}

function AdminWorkoutEditor({workout,onSave}:{workout:AdminReport['workouts'][number];onSave:(payload:unknown)=>Promise<void>}){
 const [open,setOpen]=useState(false);const [notes,setNotes]=useState(workout.notes||'');const [sportName,setSportName]=useState(workout.sport_name||'');
 const [exercises,setExercises]=useState(workout.exercises.map(x=>({exercise_name:x.exercise_name,weight:String(x.weight),reps:String(x.reps),sets:String(x.sets)})));
 const [walking,setWalking]=useState({distance:String(workout.walking?.distance??0),steps:String(workout.walking?.steps??0),calories:String(workout.walking?.calories??0),avg_speed:String(workout.walking?.avg_speed??0)});
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 function begin(){setNotes(workout.notes||'');setSportName(workout.sport_name||'');setExercises(workout.exercises.map(x=>({exercise_name:x.exercise_name,weight:String(x.weight),reps:String(x.reps),sets:String(x.sets)})));setWalking({distance:String(workout.walking?.distance??0),steps:String(workout.walking?.steps??0),calories:String(workout.walking?.calories??0),avg_speed:String(workout.walking?.avg_speed??0)});setOpen(v=>!v);}
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');const payload:Record<string,unknown>={notes};if(workout.workout_type==='Strength')payload.exercises=exercises.map(row=>({exercise_name:row.exercise_name.trim(),weight:Number(row.weight),reps:Number(row.reps),sets:Number(row.sets)}));else if(workout.workout_type==='Walking')payload.walking={distance:Number(walking.distance),steps:Number(walking.steps),calories:Number(walking.calories),avg_speed:Number(walking.avg_speed)};else payload.sport_name=sportName;try{await onSave(payload);setOpen(false);}catch(err){setError(err instanceof Error?err.message:'Could not update workout.');}finally{setBusy(false);}}
 function editExercise(index:number,key:string,value:string){setExercises(old=>old.map((row,i)=>i===index?{...row,[key]:value}:row));}
 return <div className="admin-editor"><button type="button" className="secondary-button small-button" onClick={begin}>Edit workout</button>{open&&<form className="admin-edit-form" onSubmit={submit}>{error&&<span className="form-error">{error}</span>}<label>Notes<textarea rows={2} value={notes} onChange={e=>setNotes(e.target.value)} maxLength={1000}/></label>{workout.workout_type==='Sports'&&<label>Sport<input value={sportName} onChange={e=>setSportName(e.target.value)} maxLength={80} required/></label>}{workout.workout_type==='Walking'&&<div className="admin-edit-grid">{(['distance','steps','calories','avg_speed'] as const).map(key=><label key={key}>{key.replace('_',' ')}<input type="number" min="0" step="0.1" value={walking[key]} onChange={e=>setWalking({...walking,[key]:e.target.value})} required/></label>)}</div>}{workout.workout_type==='Strength'&&<div className="admin-edit-exercises"><b>Exercises</b>{exercises.map((row,index)=><div className="admin-edit-grid" key={index}><label>Exercise<input value={row.exercise_name} onChange={e=>editExercise(index,'exercise_name',e.target.value)} maxLength={120} required/></label><label>Weight kg<input type="number" min="0" step="0.1" value={row.weight} onChange={e=>editExercise(index,'weight',e.target.value)} required/></label><label>Reps<input type="number" min="1" value={row.reps} onChange={e=>editExercise(index,'reps',e.target.value)} required/></label><label>Sets<input type="number" min="1" value={row.sets} onChange={e=>editExercise(index,'sets',e.target.value)} required/></label><button type="button" className="secondary-button small-button" disabled={exercises.length<=1} onClick={()=>setExercises(old=>old.filter((_,i)=>i!==index))}>Remove</button></div>)}<button type="button" className="secondary-button small-button" onClick={()=>setExercises(old=>[...old,{exercise_name:'',weight:'0',reps:'1',sets:'1'}])}>Add exercise</button></div>}<div className="admin-edit-actions"><button className="primary-button small-button" disabled={busy}>{busy?'Saving…':'Save workout'}</button><button type="button" className="secondary-button small-button" onClick={()=>setOpen(false)}>Cancel</button></div></form>}</div>;
}

function AdminProgressEditor({report,onSave}:{report:AdminReport['progress_reports'][number];onSave:(payload:{notes:string})=>Promise<void>}){
 const [open,setOpen]=useState(false);const [notes,setNotes]=useState(report.notes||'');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');try{await onSave({notes});setOpen(false);}catch(err){setError(err instanceof Error?err.message:'Could not update report.');}finally{setBusy(false);}}
 return <div className="admin-editor"><button type="button" className="secondary-button small-button" onClick={()=>{setNotes(report.notes||'');setOpen(v=>!v);}}>Edit report</button>{open&&<form className="admin-edit-form" onSubmit={submit}>{error&&<span className="form-error">{error}</span>}<label>Notes<textarea rows={2} maxLength={1000} value={notes} onChange={e=>setNotes(e.target.value)}/></label><div className="admin-edit-actions"><button className="primary-button small-button" disabled={busy}>{busy?'Saving…':'Save report'}</button><button type="button" className="secondary-button small-button" onClick={()=>setOpen(false)}>Cancel</button></div></form>}</div>;
}

function AdminPostEditor({caption,onSave}:{caption:string;onSave:(caption:string)=>Promise<void>}){
 const [open,setOpen]=useState(false);const [text,setText]=useState(caption);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');try{await onSave(text);setOpen(false);}catch(err){setError(err instanceof Error?err.message:'Could not update post.');}finally{setBusy(false);}}
 return <div className="admin-editor"><button type="button" className="secondary-button small-button" onClick={()=>{setText(caption);setOpen(v=>!v);}}>Edit caption</button>{open&&<form className="admin-edit-form" onSubmit={submit}>{error&&<span className="form-error">{error}</span>}<label>Caption<textarea rows={2} maxLength={500} value={text} onChange={e=>setText(e.target.value)}/></label><div className="admin-edit-actions"><button className="primary-button small-button" disabled={busy}>{busy?'Saving…':'Save caption'}</button><button type="button" className="secondary-button small-button" onClick={()=>setOpen(false)}>Cancel</button></div></form>}</div>;
}

function AdminDeleteButton({label,onDelete,onDeleted}:{label:string;onDelete:()=>Promise<{deleted:boolean}>;onDeleted:()=>Promise<void>}){
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function remove(){if(!window.confirm(`Permanently ${label.toLowerCase()}? This cannot be undone.`))return;setBusy(true);setError('');try{await onDelete();await onDeleted();}catch(err){setError(err instanceof Error?err.message:`Could not ${label.toLowerCase()}.`);}finally{setBusy(false);}}
 return <div className="admin-delete-wrap"><button type="button" className="danger-button small-button" onClick={()=>void remove()} disabled={busy}>{busy?'Deleting…':label}</button>{error&&<span className="admin-delete-error">{error}</span>}</div>;
}
