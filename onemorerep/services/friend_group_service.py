from onemorerep.database import connect, transaction


def list_groups(user_id):
    with connect() as conn:
        groups = conn.execute("""SELECT g.id,g.name,g.owner_id,gm.user_id member_id,
            u.username,u.display_name FROM friend_group_members mine
            JOIN friend_groups g ON g.id=mine.group_id
            JOIN friend_group_members gm ON gm.group_id=g.id
            JOIN users u ON u.id=gm.user_id
            WHERE mine.user_id=%s ORDER BY g.name,u.display_name""", (user_id,)).fetchall()
    result = {}
    for row in groups:
        item = result.setdefault(row["id"], {"id":row["id"],"name":row["name"],
            "owner_id":row["owner_id"],"is_owner":row["owner_id"]==user_id,"members":[]})
        item["members"].append({"id":row["member_id"],"username":row["username"],"display_name":row["display_name"],"is_me":row["member_id"]==user_id})
    return list(result.values())


def create_group(user_id, name):
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        raise ValueError("Group names must be between 1 and 60 characters.")
    with transaction() as conn:
        if conn.execute("SELECT 1 FROM friend_groups WHERE owner_id=%s AND lower(name)=lower(%s)", (user_id,name)).fetchone():
            raise ValueError("You already have a group with that name.")
        group = conn.execute("INSERT INTO friend_groups(owner_id,name) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING id,name,owner_id",
                             (user_id,name)).fetchone()
        if not group:
            raise ValueError("You already have a group with that name.")
        conn.execute("INSERT INTO friend_group_members(group_id,user_id) VALUES(%s,%s)", (group["id"],user_id))
    return {**group,"is_owner":True,"members":[{"id":user_id,"is_me":True}]}


def add_member(user_id, group_id, username):
    with transaction() as conn:
        group = conn.execute("SELECT owner_id FROM friend_groups WHERE id=%s FOR UPDATE", (group_id,)).fetchone()
        if not group or group["owner_id"] != user_id:
            raise ValueError("Only the group owner can add members.")
        member = conn.execute("SELECT id,username,display_name FROM users WHERE username=%s", ((username or "").strip(),)).fetchone()
        if not member:
            raise ValueError("No user has that username.")
        if member["id"] == user_id:
            raise ValueError("You are already in this group.")
        if not conn.execute("""SELECT 1 FROM friendships WHERE status='accepted' AND
            ((user1_id=%s AND user2_id=%s) OR (user1_id=%s AND user2_id=%s))""",
            (user_id,member["id"],member["id"],user_id)).fetchone():
            raise ValueError("You can only add accepted friends to a group.")
        conn.execute("INSERT INTO friend_group_members(group_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                     (group_id,member["id"]))
    return dict(member)


def remove_member(user_id, group_id, member_id):
    with transaction() as conn:
        group = conn.execute("SELECT owner_id FROM friend_groups WHERE id=%s FOR UPDATE", (group_id,)).fetchone()
        if not group:
            raise ValueError("Group not found.")
        if user_id != group["owner_id"] and user_id != member_id:
            raise ValueError("Only the group owner can remove other members.")
        if member_id == group["owner_id"]:
            raise ValueError("The owner cannot leave; delete the group instead.")
        conn.execute("DELETE FROM friend_group_members WHERE group_id=%s AND user_id=%s", (group_id,member_id))


def delete_group(user_id, group_id):
    with transaction() as conn:
        deleted = conn.execute("DELETE FROM friend_groups WHERE id=%s AND owner_id=%s RETURNING id",
                               (group_id,user_id)).fetchone()
    if not deleted:
        raise ValueError("Only the group owner can delete this group.")


def member_ids(conn, user_id, group_id=None):
    if group_id is not None:
        if not conn.execute("SELECT 1 FROM friend_group_members WHERE group_id=%s AND user_id=%s", (group_id,user_id)).fetchone():
            raise ValueError("That group is unavailable.")
        return [row["user_id"] for row in conn.execute(
            "SELECT user_id FROM friend_group_members WHERE group_id=%s", (group_id,)).fetchall()]
    ids = [user_id]
    ids.extend(row["friend_id"] for row in conn.execute("""SELECT CASE WHEN user1_id=%s THEN user2_id ELSE user1_id END friend_id
        FROM friendships WHERE status='accepted' AND (user1_id=%s OR user2_id=%s)""",
        (user_id,user_id,user_id)).fetchall())
    return ids
