import type { Achievement, AdminAccount, AdminReport, Dashboard, ExpRecord, FeedComment, FeedPost, FriendList, LeaderboardRow, ProgressReport, Statistics, User, Workout, WorkoutDetail } from "@/types";

const configuredApiBase = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "");
const pointsToThisComputer = /^https?:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?$/i.test(configuredApiBase || "");

export const API_BASE = process.env.NODE_ENV === "development"
  ? configuredApiBase || "http://127.0.0.1:8000"
  : configuredApiBase && !pointsToThisComputer
    ? configuredApiBase
    : "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/me"),
  adminUsers: () => request<AdminAccount[]>("/api/admin/users"),
  adminReport: (id: number) => request<AdminReport>(`/api/admin/users/${id}`),
  adminUpdateMember: (id:number, display_name:string) => request(`/api/admin/users/${id}`, { method:"PUT", body:JSON.stringify({display_name}) }),
  adminUpdateWorkout: (userId:number,id:number,payload:unknown) => request(`/api/admin/users/${userId}/workouts/${id}`, { method:"PUT", body:JSON.stringify(payload) }),
  adminUpdateProgress: (userId:number,id:number,payload:{weight_kg:number;notes:string}) => request(`/api/admin/users/${userId}/progress/${id}`, { method:"PUT", body:JSON.stringify(payload) }),
  adminUpdatePost: (userId:number,id:number,caption:string) => request(`/api/admin/users/${userId}/posts/${id}`, { method:"PUT", body:JSON.stringify({caption}) }),
  adminDeleteMember: (id:number) => request<{deleted:boolean}>(`/api/admin/users/${id}`, { method:"DELETE" }),
  adminDeleteWorkout: (userId:number,id:number) => request<{deleted:boolean}>(`/api/admin/users/${userId}/workouts/${id}`, { method:"DELETE" }),
  adminDeleteProgress: (userId:number,id:number) => request<{deleted:boolean}>(`/api/admin/users/${userId}/progress/${id}`, { method:"DELETE" }),
  adminDeletePost: (userId:number,id:number) => request<{deleted:boolean}>(`/api/admin/users/${userId}/posts/${id}`, { method:"DELETE" }),
  adminDeleteComment: (userId:number,id:number) => request<{deleted:boolean}>(`/api/admin/users/${userId}/comments/${id}`, { method:"DELETE" }),
  login: (username: string, password: string) => request<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  register: (username: string, display_name: string, password: string) => request<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ username, display_name, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  workouts: () => request<Workout[]>("/api/activities"),
  activityDetail: (id: number) => request<WorkoutDetail>(`/api/activities/${id}`),
  exp: () => request<ExpRecord[]>("/api/exp"),
  statistics: () => request<Statistics>("/api/statistics"),
  achievements: () => request<Achievement[]>("/api/achievements"),
  leaderboard: () => request<LeaderboardRow[]>("/api/leaderboard"),
  feed: () => request<FeedPost[]>("/api/feed"),
  like: (id: number) => request<{ liked: boolean; likes_count: number }>(`/api/feed/${id}/likes`, { method: "POST" }),
  unlike: (id: number) => request<{ liked: boolean; likes_count: number }>(`/api/feed/${id}/likes`, { method: "DELETE" }),
  comments: (id: number) => request<FeedComment[]>(`/api/feed/${id}/comments`),
  addComment: (id: number, body: string) => request<{ id: number; comments_count: number }>(`/api/feed/${id}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
  progress: () => request<ProgressReport[]>("/api/progress"),
  saveProgress: (form: FormData) => request<{ id: number }>("/api/progress", { method: "POST", body: form }),
  friends: () => request<FriendList>("/api/friends"),
  addFriend: (username: string) => request<{ status: string }>("/api/friends/requests", { method: "POST", body: JSON.stringify({ username }) }),
  respondFriend: (id: number, accept: boolean) => request<{ status: string }>(`/api/friends/requests/${id}`, { method: "POST", body: JSON.stringify({ accept }) }),
  createWorkout: (payload: unknown, photo?: File | null) => {
    if (!photo) return request<{ id: number; exp_earned: number; duration_seconds: number }>("/api/activities", { method: "POST", body: JSON.stringify(payload) });
    const form = new FormData(); form.set("activity", JSON.stringify(payload)); form.set("workout_image", photo);
    return request<{ id: number; exp_earned: number; duration_seconds: number }>("/api/activities", { method: "POST", body: form });
  },
  share: (form: FormData) => request<{ id: number }>("/api/feed", { method: "POST", body: form }),
};
