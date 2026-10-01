from onemorerep.database import transaction, connect

def send_request(user_id, username):
    with transaction() as c:
        other=c.execute("SELECT id FROM users WHERE username=%s",(username.strip(),)).fetchone()
        if not other: raise ValueError("No user has that username.")
        if other["id"]==user_id: raise ValueError("You cannot add yourself.")
        a,b=sorted((user_id,other["id"]))
        row=c.execute("SELECT status FROM friendships WHERE user1_id=%s AND user2_id=%s FOR UPDATE",(a,b)).fetchone()
        if row and row["status"]=="accepted": raise ValueError("You are already friends.")
        if row and row["status"]=="pending": raise ValueError("A request already exists.")
        if row: c.execute("UPDATE friendships SET status='pending',request_from=%s,created_at=now() WHERE user1_id=%s AND user2_id=%s",(user_id,a,b))
        else: c.execute("INSERT INTO friendships(user1_id,user2_id,request_from,status) VALUES(%s,%s,%s,'pending')",(a,b,user_id))

def requests_and_friends(user_id):
    with connect() as c:
        incoming=c.execute("SELECT f.id,u.username,u.display_name FROM friendships f JOIN users u ON u.id=f.request_from WHERE f.request_from<>%s AND (f.user1_id=%s OR f.user2_id=%s) AND f.status='pending' ORDER BY f.created_at",(user_id,user_id,user_id)).fetchall()
        outgoing=c.execute("SELECT u.username,u.display_name FROM friendships f JOIN users u ON u.id=CASE WHEN f.user1_id=%s THEN f.user2_id ELSE f.user1_id END WHERE f.request_from=%s AND f.status='pending'",(user_id,user_id)).fetchall()
        friends=c.execute("SELECT u.username,u.display_name FROM friendships f JOIN users u ON u.id=CASE WHEN f.user1_id=%s THEN f.user2_id ELSE f.user1_id END WHERE (f.user1_id=%s OR f.user2_id=%s) AND f.status='accepted' ORDER BY u.display_name",(user_id,user_id,user_id)).fetchall()
    return incoming,outgoing,friends

def respond(user_id, friendship_id, accept):
    with transaction() as c:
        row=c.execute("SELECT request_from,user1_id,user2_id FROM friendships WHERE id=%s AND status='pending' FOR UPDATE",(friendship_id,)).fetchone()
        if not row or row["request_from"]==user_id or user_id not in (row["user1_id"],row["user2_id"]):
            raise ValueError("This request is unavailable.")
        c.execute("UPDATE friendships SET status=%s WHERE id=%s",("accepted" if accept else "rejected",friendship_id))

def workout_detail(user_id,workout_id):
    with connect() as c:
        workout=c.execute("SELECT workout_type FROM workouts WHERE id=%s AND user_id=%s",(workout_id,user_id)).fetchone()
        if not workout: raise ValueError("Activity not found.")
        if workout["workout_type"]=="Strength":
            rows=c.execute("SELECT exercise_name,weight,reps,sets FROM exercises WHERE workout_id=%s ORDER BY id",(workout_id,)).fetchall()
            return {"workout_type":"Strength","details":[{"exercise_name":r["exercise_name"],"weight":r["weight"],"reps":r["reps"],"sets":r["sets"]} for r in rows]}
        if workout["workout_type"]=="Sports":
            row=c.execute("SELECT sport_name FROM sports WHERE workout_id=%s",(workout_id,)).fetchone()
            return {"workout_type":"Sports","details":[{"sport_name":row["sport_name"]}] if row else []}
        r=c.execute("SELECT distance,steps,calories,avg_speed FROM walking WHERE workout_id=%s",(workout_id,)).fetchone()
        return {"workout_type":"Walking","details":dict(r) if r else {}}
