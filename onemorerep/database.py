from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
import config


def connect():
    return psycopg.connect(host=config.DB_HOST, port=config.DB_PORT,
                           user=config.DB_USER, password=config.DB_PASSWORD,
                           dbname=config.DB_NAME, row_factory=dict_row, connect_timeout=5,
                           prepare_threshold=None)


@contextmanager
def transaction(conn=None):
    own = conn is None
    connection = conn or connect()
    try:
        with connection.transaction():
            yield connection
    finally:
        if own:
            connection.close()


def initialize_schema():
    """Inspect legacy tables, bootstrap only a wholly empty DB, then add app tables."""
    base_tables = {"users", "workouts", "exercises", "walking", "streaks"}
    base_schema = [
        """CREATE TABLE users (
            id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE workouts (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workout_type TEXT NOT NULL, workout_date DATE NOT NULL, start_time TIME NOT NULL,
            end_time TIME NOT NULL, duration INTEGER NOT NULL CHECK(duration >= 0), notes TEXT NOT NULL DEFAULT '')""",
        """CREATE TABLE exercises (
            id BIGSERIAL PRIMARY KEY, workout_id BIGINT NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL, weight NUMERIC(12,3) NOT NULL CHECK(weight >= 0),
            reps INTEGER NOT NULL CHECK(reps >= 0), sets INTEGER NOT NULL CHECK(sets >= 0))""",
        """CREATE TABLE walking (
            id BIGSERIAL PRIMARY KEY, workout_id BIGINT NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            distance NUMERIC(12,3) NOT NULL CHECK(distance >= 0), steps BIGINT NOT NULL CHECK(steps >= 0),
            calories NUMERIC(12,3) NOT NULL CHECK(calories >= 0), avg_speed NUMERIC(12,3) NOT NULL CHECK(avg_speed >= 0))""",
        """CREATE TABLE streaks (
            user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            current_streak INTEGER NOT NULL DEFAULT 0, longest_streak INTEGER NOT NULL DEFAULT 0,
            last_workout_date DATE)""",
    ]
    statements = [
        """CREATE TABLE IF NOT EXISTS exp_records (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workout_id BIGINT NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
            activity_date DATE NOT NULL, activity_period TEXT NOT NULL CHECK(activity_period IN ('morning','evening')),
            exp_amount INTEGER NOT NULL CHECK(exp_amount IN (20,30)), earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(user_id, activity_date, activity_period), UNIQUE(workout_id)
        )""",
        """CREATE TABLE IF NOT EXISTS exp_adjustments (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            admin_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            admin_username TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0,
            weekly_amount INTEGER NOT NULL DEFAULT 0, monthly_amount INTEGER NOT NULL DEFAULT 0,
            current_streak_delta INTEGER NOT NULL DEFAULT 0, longest_streak_delta INTEGER NOT NULL DEFAULT 0,
            workout_delta INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL CHECK(length(reason) BETWEEN 1 AND 250),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT exp_adjustments_any_change_check CHECK(amount<>0 OR weekly_amount<>0 OR monthly_amount<>0 OR
              current_streak_delta<>0 OR longest_streak_delta<>0 OR workout_delta<>0))""",
        """CREATE TABLE IF NOT EXISTS friendships (
            id BIGSERIAL PRIMARY KEY, user1_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            user2_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            request_from BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('pending','accepted','rejected')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK(user1_id < user2_id), UNIQUE(user1_id,user2_id)
        )""",
        """CREATE TABLE IF NOT EXISTS friend_groups (
            id BIGSERIAL PRIMARY KEY, owner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 60),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(owner_id,name))""",
        """CREATE TABLE IF NOT EXISTS friend_group_members (
            group_id BIGINT NOT NULL REFERENCES friend_groups(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(group_id,user_id))""",
        """CREATE TABLE IF NOT EXISTS achievements (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            badge_name TEXT NOT NULL, earned_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id,badge_name)
        )""",
        """CREATE TABLE IF NOT EXISTS web_sessions (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash CHAR(64) NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS feed_posts (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            workout_id BIGINT UNIQUE REFERENCES workouts(id) ON DELETE SET NULL,
            achievement_id BIGINT REFERENCES achievements(id) ON DELETE SET NULL,
            caption TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CHECK(length(caption) <= 500))""",
        """CREATE TABLE IF NOT EXISTS feed_images (
            id BIGSERIAL PRIMARY KEY, post_id BIGINT NOT NULL UNIQUE REFERENCES feed_posts(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL UNIQUE, mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK(size_bytes BETWEEN 1 AND 8388608),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS workout_images (
            workout_id BIGINT PRIMARY KEY REFERENCES workouts(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL UNIQUE, mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK(size_bytes BETWEEN 1 AND 8388608),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS progress_reports (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            report_date DATE NOT NULL, weight_kg NUMERIC(6,2) CHECK(weight_kg IS NULL OR (weight_kg > 0 AND weight_kg <= 500)),
            notes TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id,report_date), CHECK(length(notes) <= 1000))""",
        """CREATE TABLE IF NOT EXISTS progress_images (
            report_id BIGINT PRIMARY KEY REFERENCES progress_reports(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL UNIQUE, mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK(size_bytes BETWEEN 1 AND 8388608),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS sports (
            workout_id BIGINT PRIMARY KEY REFERENCES workouts(id) ON DELETE CASCADE,
            sport_name TEXT NOT NULL CHECK(length(sport_name) BETWEEN 1 AND 80))""",
        """CREATE TABLE IF NOT EXISTS feed_likes (
            post_id BIGINT NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(post_id,user_id))""",
        """CREATE TABLE IF NOT EXISTS feed_comments (
            id BIGSERIAL PRIMARY KEY, post_id BIGINT NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        "CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, workout_date)",
        "CREATE INDEX IF NOT EXISTS idx_exp_user_date ON exp_records(user_id, activity_date)",
        "CREATE INDEX IF NOT EXISTS idx_exp_adjustments_user_created ON exp_adjustments(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_friendships_accepted ON friendships(user1_id,user2_id) WHERE status='accepted'",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_friend_groups_owner_name ON friend_groups(owner_id,lower(name))",
        "CREATE INDEX IF NOT EXISTS idx_friend_group_members_user ON friend_group_members(user_id,group_id)",
        "CREATE INDEX IF NOT EXISTS idx_feed_posts_created ON feed_posts(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_progress_reports_user_date ON progress_reports(user_id,report_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_feed_comments_post_created ON feed_comments(post_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON web_sessions(expires_at)",
    ]
    with transaction() as conn:
        rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'").fetchall()
        existing = {r["table_name"] for r in rows}
        app_tables = existing & base_tables
        if not app_tables:
            for sql in base_schema:
                conn.execute(sql)
        elif app_tables != base_tables:
            missing = ", ".join(sorted(base_tables - app_tables))
            raise RuntimeError(f"Found a partial legacy schema. Missing tables: {missing}. No legacy tables were changed.")
        required = {
            "users": {"id", "username", "password_hash", "display_name", "created_at"},
            "workouts": {"id", "user_id", "workout_type", "workout_date", "start_time", "end_time", "duration", "notes"},
            "exercises": {"id", "workout_id", "exercise_name", "weight", "reps", "sets"},
            "walking": {"id", "workout_id", "distance", "steps", "calories", "avg_speed"},
            "streaks": {"user_id", "current_streak", "longest_streak", "last_workout_date"},
        }
        rows = conn.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=current_schema()").fetchall()
    found = {}
    for row in rows:
        found.setdefault(row["table_name"], set()).add(row["column_name"])
    missing = {t: sorted(cols - found.get(t, set())) for t, cols in required.items() if cols - found.get(t, set())}
    if missing:
        details = "; ".join(f"{table}: {', '.join(cols)}" for table, cols in missing.items())
        raise RuntimeError("Existing PostgreSQL schema is incompatible. Missing tables/columns: " + details +
                           ". No existing tables were altered or removed; review the schema before migration.")
    with transaction() as conn:
        for sql in statements:
            conn.execute(sql)
        for column in ("weekly_amount", "monthly_amount", "current_streak_delta", "longest_streak_delta", "workout_delta"):
            conn.execute(f"ALTER TABLE exp_adjustments ADD COLUMN IF NOT EXISTS {column} INTEGER NOT NULL DEFAULT 0")
        conn.execute("ALTER TABLE exp_adjustments DROP CONSTRAINT IF EXISTS exp_adjustments_amount_check")
        conn.execute("""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='exp_adjustments_any_change_check') THEN
              ALTER TABLE exp_adjustments ADD CONSTRAINT exp_adjustments_any_change_check CHECK(
                amount<>0 OR weekly_amount<>0 OR monthly_amount<>0 OR current_streak_delta<>0 OR
                longest_streak_delta<>0 OR workout_delta<>0);
            END IF;
        END $$""")
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
        conn.execute("""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='users_role_check') THEN
              ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('user','admin'));
            END IF;
        END $$""")
        conn.execute("ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS achievement_id BIGINT REFERENCES achievements(id) ON DELETE SET NULL")
        conn.execute("ALTER TABLE progress_reports ALTER COLUMN weight_kg DROP NOT NULL")
        conn.execute("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS request_from BIGINT REFERENCES users(id) ON DELETE CASCADE")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_streaks_user_unique ON streaks(user_id)")
