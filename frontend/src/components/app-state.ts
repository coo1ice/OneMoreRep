import type {
  Achievement,
  AdminAccount,
  Dashboard,
  ExpRecord,
  FeedPost,
  FriendGroup,
  FriendList,
  LeaderboardRow,
  ProgressReport,
  Statistics,
  Workout,
} from '@/types';

export type AppData = {
  dashboard: Dashboard | null;
  workouts: Workout[];
  expRows: ExpRecord[];
  friendList: FriendList | null;
  groups: FriendGroup[];
  posts: FeedPost[];
  leaderboard: LeaderboardRow[];
  stats: Statistics | null;
  achievements: Achievement[];
  progressReports: ProgressReport[];
  adminUsers: AdminAccount[];
};

export const initialAppData: AppData = {
  dashboard: null,
  workouts: [],
  expRows: [],
  friendList: null,
  groups: [],
  posts: [],
  leaderboard: [],
  stats: null,
  achievements: [],
  progressReports: [],
  adminUsers: [],
};

export function appDataReducer(state: AppData, update: Partial<AppData>): AppData {
  return { ...state, ...update };
}
