import bcrypt
from onemorerep.database import connect, transaction

def register(username,password,display_name):
    username=username.strip(); display_name=display_name.strip()
    if not username or not password or not display_name: raise ValueError("All fields are required.")
    if len(password)<8: raise ValueError("Password must be at least 8 characters.")
    hashed=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()
    try:
        with transaction() as conn:
            row=conn.execute("INSERT INTO users(username,password_hash,display_name) VALUES(%s,%s,%s) RETURNING id",(username,hashed,display_name)).fetchone()
            conn.execute("INSERT INTO streaks(user_id,current_streak,longest_streak) VALUES(%s,0,0)",(row["id"],))
            return row["id"]
    except Exception as exc:
        if getattr(exc,"sqlstate",None)=="23505": raise ValueError("That username is already registered.") from exc
        raise

def login(username,password):
    with connect() as conn:
        row=conn.execute("SELECT id,username,display_name,role,password_hash FROM users WHERE username=%s",(username.strip(),)).fetchone()
    if not row or not bcrypt.checkpw(password.encode(),row["password_hash"].encode()): return None
    return {k:row[k] for k in ("id","username","display_name","role")}
