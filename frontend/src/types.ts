export type User = { id: number; username: string; display_name: string; role: 'user' | 'admin' };
export type AdminAccount = User & { created_at: string; total_exp:number; workout_count: number; progress_count: number; post_count: number };
export type AdminReport = {
  user: AdminAccount;
  exp_adjustments:Array<{amount:number;reason:string;admin_username:string;created_at:string}>;
  workouts: Array<{ id:number; workout_type:string; workout_date:string; start_time:string; duration:number; notes:string; exp_amount:number|null; sport_name:string|null; walking:{distance:number;steps:number;calories:number;avg_speed:number}|null; exercises:Array<{exercise_name:string;weight:number;reps:number;sets:number}>; image_url:string|null }>;
  progress_reports: Array<{ id:number; report_date:string; notes:string; image_url:string|null }>;
  posts: Array<{ id:number; caption:string; created_at:string; workout_id:number|null; achievement_name:string|null; image_url:string|null; likes_count:number; comments_count:number }>;
  comments: Array<{ id:number; post_id:number; commenter:string; body:string; created_at:string }>;
  likes: Array<{ post_id:number; liker:string; created_at:string }>;
};
export type Dashboard = {
  name: string; streak: { current_streak: number; longest_streak: number } | null;
  today: number; total: number; morning: number; morning_duration: number;
  evening: number; evening_duration: number; rank: number | null;
};
export type Workout = {
  id: number; workout_date: string; workout_type: "Strength" | "Walking" | "Sports";
  duration: number; start_time: string; exp_amount: number | null; has_image: boolean;
};
export type ExpRecord = {
  activity_date: string; activity_period: "morning" | "evening" | "admin_adjustment";
  workout_type: string; duration: number | null; exp_amount: number;
  source:"workout"|"admin_adjustment"; reason:string|null; admin_username:string|null;
};
export type FeedPost = {
  id: number; user_id: number; display_name: string; workout_id: number | null;
  achievement_id: number | null; achievement_name: string | null;
  caption: string; created_at: string; workout_type: string | null;
  workout_date: string | null; duration: number | null; exp_amount: number | null;
  image_url: string | null; likes_count: number; liked_by_me: boolean; comments_count: number;
};
export type FeedComment = { id: number; user_id: number; display_name: string; body: string; created_at: string };
export type ProgressReport = {
  id: number; report_date: string; notes: string; image_url: string | null;
  created_at: string; updated_at: string;
};
export type Friend = { username: string; display_name: string };
export type FriendRequest = Friend & { id: number };
export type FriendList = { incoming: FriendRequest[]; outgoing: Friend[]; friends: Friend[] };
export type FriendGroup = { id:number; name:string; owner_id:number; is_owner:boolean; members:Array<{id:number;username?:string;display_name?:string;is_me?:boolean}> };
export type Statistics = {
  total_exp: number; total_workouts: number; strength_workouts: number;
  walking_sessions: number; sports_sessions: number; total_weight: number; total_distance: number;
  total_steps: number; longest_streak: number; current_streak: number;
};
export type LeaderboardRow = {
  id: number; display_name: string; total_exp: number; weekly_exp: number;
  monthly_exp: number; current_streak: number; longest_streak: number; total_workouts: number;
};
export type Achievement = { id: number; badge_name: string; earned_at: string };
export type WorkoutDetail = {
  workout_type: "Strength" | "Walking" | "Sports";
  details: Array<Record<string, string | number>>;
};
