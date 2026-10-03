'use client';

import { useCallback, useEffect, useReducer, useRef, useState, type FormEvent } from 'react';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { Activity, BarChart3, Check, Clock3, LayoutDashboard, LoaderCircle, LogOut, Menu, Plus, ShieldCheck, Sparkles, Trophy, UserPlus, UserRound, Users, X } from 'lucide-react';
import { api } from '@/lib/api';
import type { User } from '@/types';
import type { View } from '@/components/views/types';
import { durationLabel, initials, LoadingSkeleton } from '@/components/views/shared';
import { appDataReducer, initialAppData } from '@/components/app-state';
import { AuthScreen } from '@/components/views/auth';
import { DashboardView } from '@/components/views/dashboard';
import { FeedView } from '@/components/views/feed';
import { ActivityView, ProgressView } from '@/components/views/activity';
import { FriendsView } from '@/components/views/friends';
import { ExpView, HistoryView, LeaderboardView, ProfileView, StatisticsView } from '@/components/views/records';
import { AdminView } from '@/components/views/admin';

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
  const [data, patchData] = useReducer(appDataReducer, initialAppData);
  const { dashboard, workouts, expRows, friendList, groups, posts, leaderboard, stats, achievements, progressReports, adminUsers } = data;
  const loadAdminUser = useCallback((id:number) => api.adminReport(id), []);
  const reloadAdminUsers = useCallback(async () => { const rows=await api.adminUsers(); patchData({adminUsers:rows}); return rows; }, []);

  useEffect(() => {
    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.has('password')) {
      currentUrl.searchParams.delete('username');
      currentUrl.searchParams.delete('password');
      window.history.replaceState(window.history.state, '', `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
    }
    api.bootstrap().then((initial) => {
      patchData({dashboard:initial.dashboard,posts:initial.feed,workouts:initial.workouts});
      initialDashboardLoaded.current = true;
      setUser(initial.user);
      void api.friends().then(friendList=>patchData({friendList})).catch(() => patchData({friendList:{incoming:[],outgoing:[],friends:[]}}));
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
        const [dashboard, posts, workouts, friendList] = await Promise.all([api.dashboard(), api.feed(), api.workouts(), api.friends()]); patchData({dashboard,posts,workouts,friendList});
      } else if (selected === 'feed') {
        const [posts, workouts, achievements] = await Promise.all([api.feed(), api.workouts(), api.achievements()]); patchData({posts,workouts,achievements});
      } else if (selected === 'activity' || selected === 'history') patchData({workouts:await api.workouts()});
      else if (selected === 'progress') patchData({progressReports:await api.progress()});
      else if (selected === 'exp') patchData({expRows:await api.exp()});
      else if (selected === 'friends') { const [friendList,groups]=await Promise.all([api.friends(),api.groups()]);patchData({friendList,groups}); }
      else if (selected === 'leaderboard') { const [groups,leaderboard]=await Promise.all([api.groups(),api.leaderboard()]);patchData({groups,leaderboard}); }
      else if (selected === 'statistics') patchData({stats:await api.statistics()});
      else if (selected === 'profile') { const [stats,achievements]=await Promise.all([api.statistics(),api.achievements()]);patchData({stats,achievements}); }
      else if (selected === 'admin' && user.role === 'admin') patchData({adminUsers:await api.adminUsers()});
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
    try { await api.deletePost(id); patchData({posts:posts.filter(post=>post.id!==id)}); setNotice('Your post was deleted.'); }
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
      patchData({friendList:await api.friends()});
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
        <div className="topbar-right"><span className="top-exp"><Sparkles size={15} /> {dashboard?.total?.toLocaleString() ?? '—'} EXP</span><button className="avatar" title={user.display_name}>{initials(user.display_name)}</button></div>
      </header>

      <div className="workspace">
        <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
          <div className="sidebar-label">YOUR SPACE</div>
          <nav aria-label="Main navigation">
            {[...nav, ...(user.role === 'admin' ? [{ id: 'admin' as const, label: 'Admin', icon: ShieldCheck }] : [])].map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${view === id ? 'nav-active' : ''}`} onClick={() => selectView(id)}><Icon size={18} strokeWidth={2} /><span>{label}</span></button>)}
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
            {view === 'leaderboard' && <LeaderboardView rows={leaderboard} groups={groups} currentId={user.id} onSelectGroup={async(id)=>{setBusy(true);setError('');try{patchData({leaderboard:await api.leaderboard(id)});}catch(e){setError(e instanceof Error?e.message:'Could not load leaderboard.');}finally{setBusy(false);}}} />}
            {view === 'statistics' && <StatisticsView data={stats} />}
            {view === 'profile' && <ProfileView user={user} stats={stats} achievements={achievements} onSignOut={signOut} />}
            {view === 'admin' && user.role === 'admin' && <AdminView users={adminUsers} actorId={user.id} onLoadUser={loadAdminUser} onReloadUsers={reloadAdminUsers} onAdjustLeaderboard={async(id,changes,reason)=>{await api.adminAdjustLeaderboard(id,changes,reason);setNotice('Leaderboard values updated.');}} />}
          </div>
        </main>
      </div>
    </div>
  );
}
