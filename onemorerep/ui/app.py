import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, time
import config
from onemorerep import auth
from onemorerep.database import connect
from onemorerep.services import report_service, leaderboard_service
from onemorerep.services import friend_service
from onemorerep.services.workout_service import save_activity

BG="#10151d"; CARD="#1b2430"; FG="#edf2f7"; ACC="#65d6ad"

class OneMoreRepApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("OneMoreRep"); self.geometry("1000x700"); self.configure(bg=BG); self.user=None
        self.style=ttk.Style(self); self.style.theme_use("clam"); self.style.configure("TFrame",background=BG); self.style.configure("TLabel",background=BG,foreground=FG,font=("Segoe UI",11)); self.style.configure("TButton",padding=8)
        self.show_login()
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def show_login(self):
        self.clear(); frame=ttk.Frame(self,padding=50); frame.pack(expand=True)
        ttk.Label(frame,text="OneMoreRep",font=("Segoe UI",28,"bold")).pack(pady=12)
        self.login_user=self.field(frame,"Username"); self.login_pass=self.field(frame,"Password",True)
        ttk.Button(frame,text="Login",command=self.do_login).pack(fill="x",pady=8); ttk.Button(frame,text="Create account",command=self.show_register).pack(fill="x")
    def field(self,parent,label,secret=False):
        ttk.Label(parent,text=label).pack(anchor="w",pady=(8,2)); e=ttk.Entry(parent,show="•" if secret else ""); e.pack(fill="x"); return e
    def do_login(self):
        try: self.user=auth.login(self.login_user.get(),self.login_pass.get())
        except Exception: return messagebox.showerror("Connection error","Could not connect to OneMoreRep. Check PostgreSQL is running and database settings are correct.")
        if not self.user: return messagebox.showerror("Login failed","Username or password is incorrect.")
        self.show_main()
    def show_register(self):
        self.clear(); f=ttk.Frame(self,padding=50); f.pack(expand=True); ttk.Label(f,text="Create account",font=("Segoe UI",22,"bold")).pack(pady=10)
        self.reg_user=self.field(f,"Username"); self.reg_name=self.field(f,"Display name"); self.reg_pass=self.field(f,"Password (8+ characters)",True)
        ttk.Button(f,text="Register",command=self.do_register).pack(fill="x",pady=12); ttk.Button(f,text="Back to login",command=self.show_login).pack(fill="x")
    def do_register(self):
        try: auth.register(self.reg_user.get(),self.reg_pass.get(),self.reg_name.get()); messagebox.showinfo("Registered","Account created. Please log in."); self.show_login()
        except ValueError as e: messagebox.showerror("Registration failed",str(e))
        except Exception: messagebox.showerror("Registration failed","Could not create the account. Check the database connection and try again.")
    def show_main(self):
        self.clear(); nav=ttk.Frame(self,padding=8); nav.pack(fill="x")
        for title,fn in [("Dashboard",self.dashboard),("New Activity",self.new_activity),("History",self.show_history),("EXP",self.show_exp),("Leaderboard",self.show_leaderboard),("Statistics",self.show_stats),("Profile",self.profile),("Logout",self.logout)]: ttk.Button(nav,text=title,command=fn).pack(side="left",padx=2)
        self.body=ttk.Frame(self,padding=24); self.body.pack(fill="both",expand=True); self.dashboard()
    def heading(self,text):
        for w in self.body.winfo_children(): w.destroy()
        ttk.Label(self.body,text=text,font=("Segoe UI",22,"bold")).pack(anchor="w",pady=(0,18))
    def dashboard(self):
        self.heading("Dashboard")
        try: d=report_service.dashboard(self.user["id"])
        except Exception: ttk.Label(self.body,text="Could not load dashboard. Check the PostgreSQL connection.").pack(); return
        ttk.Label(self.body,text=f"Welcome, {d['name']}",font=("Segoe UI",20)).pack(anchor="w",pady=8)
        streak=d["streak"]; current=streak["current_streak"] if streak else 0; longest=streak["longest_streak"] if streak else 0
        now=datetime.now().time()
        def status(period, amount, start, end):
            if amount: return f"+{amount} EXP · Completed"
            if now < time.fromisoformat(start): return "Not started"
            if now <= time.fromisoformat(end): return "In progress · Not completed"
            return "Not completed"
        for text in (f"🔥 {current} day streak  ·  Best: {longest}",f"⭐ {d['total']:,} EXP total",f"Today's EXP: {d['today']} / 50",f"🌅 Morning: {status('morning',d['morning'],config.MORNING_START,config.MORNING_END)}",f"🌆 Evening: {status('evening',d['evening'],config.EVENING_START,config.EVENING_END)}",f"🏆 Rank: #{d['rank']}"):
            ttk.Label(self.body,text=text,font=("Segoe UI",15)).pack(anchor="w",pady=7)
    def new_activity(self):
        self.heading("New Activity"); f=self.body
        self.kind=tk.StringVar(value="Strength"); ttk.Label(f,text="Activity type").pack(anchor="w"); ttk.Combobox(f,textvariable=self.kind,values=["Strength","Walking"],state="readonly").pack(anchor="w")
        self.date_entry=self.field(f,"Date (YYYY-MM-DD)"); self.date_entry.insert(0,date.today().isoformat()); self.start_entry=self.field(f,"Start time (HH:MM)"); self.end_entry=self.field(f,"End time (HH:MM)"); self.notes=self.field(f,"Notes (optional)")
        self.detail=tk.Text(f,height=7,width=75,bg=CARD,fg=FG,insertbackground=FG); ttk.Label(f,text="Strength: one exercise per line: name,weight,reps,sets | Walking: distance,steps,calories,avg_speed").pack(anchor="w",pady=5); self.detail.pack(anchor="w")
        ttk.Button(f,text="Save activity",command=self.save_activity).pack(anchor="w",pady=10)
    def save_activity(self):
        try:
            day=date.fromisoformat(self.date_entry.get().strip()); kind=self.kind.get(); raw=self.detail.get("1.0","end").strip()
            if kind=="Strength":
                exercises=[]
                for line in raw.splitlines():
                    name,weight,reps,sets=[x.strip() for x in line.split(",")]; exercises.append(dict(exercise_name=name,weight=weight,reps=reps,sets=sets))
                kwargs={"exercises":exercises}
            else:
                distance,steps,calories,speed=[x.strip() for x in raw.split(",")]; kwargs={"walking":dict(distance=distance,steps=steps,calories=calories,avg_speed=speed)}
            _,xp,seconds=save_activity(self.user["id"],kind,day,self.start_entry.get(),self.end_entry.get(),self.notes.get(),**kwargs)
            messagebox.showinfo("Saved",f"Activity saved · {seconds//60} min · +{xp} EXP"); self.dashboard()
        except ValueError as e: messagebox.showerror("Could not save activity",str(e))
        except Exception: messagebox.showerror("Could not save activity","The activity could not be saved. Check the database connection and your entered values.")
    def table(self,headers,rows):
        tree=ttk.Treeview(self.body,columns=headers,show="headings",height=20)
        for h in headers: tree.heading(h,text=h); tree.column(h,width=130)
        for row in rows: tree.insert("","end",values=row)
        tree.pack(fill="both",expand=True); return tree
    def show_history(self):
        self.heading("Activity History"); rows=report_service.history(self.user["id"]); tree=self.table(("Date","Activity","Duration (min)","EXP"),[(r["workout_date"],r["workout_type"],round(r["duration"]/60),r["exp_amount"] or 0) for r in rows]); tree.bind("<Double-1>",lambda _e:self.activity_detail(tree,rows))
    def activity_detail(self,tree,rows):
        selection=tree.selection()
        if not selection: return
        row=rows[tree.index(selection[0])]
        try: details=friend_service.workout_detail(self.user["id"],row["id"])
        except ValueError as e: return messagebox.showerror("Activity details",str(e))
        except Exception: return messagebox.showerror("Activity details","Could not load these details from the database.")
        messagebox.showinfo(f"{row['workout_type']} details","\n".join(" · ".join(map(str,item)) for item in details) or "No details saved.")
    def show_exp(self):
        self.heading("EXP History"); rows=report_service.history(self.user["id"],True); self.table(("Date","Period","Activity","Duration (min)","EXP"),[(r["activity_date"],r["activity_period"].title(),r["workout_type"],round(r["duration"]/60),r["exp_amount"]) for r in rows])
    def show_leaderboard(self):
        self.heading("Leaderboard")
        with connect() as c: rows=leaderboard_service.leaderboard(c)
        self.table(("Name","Total EXP","Weekly","Monthly","Current streak","Best streak","Workouts"),[(r["display_name"],r["total_exp"],r["weekly_exp"],r["monthly_exp"],r["current_streak"],r["longest_streak"],r["total_workouts"]) for r in rows])
    def show_stats(self):
        self.heading("Statistics"); s=report_service.statistics(self.user["id"])
        for k,v in s.items(): ttk.Label(self.body,text=f"{k.replace('_',' ').title()}: {v}").pack(anchor="w",pady=5)
    def profile(self):
        self.heading("Profile"); ttk.Label(self.body,text=f"Username: {self.user['username']}\nDisplay name: {self.user['display_name']}").pack(anchor="w")
        ttk.Button(self.body,text="Friends and requests",command=self.friends).pack(anchor="w",pady=16)
    def friends(self):
        incoming,outgoing,friends=friend_service.requests_and_friends(self.user["id"])
        win=tk.Toplevel(self); win.title("Friends"); win.configure(bg=BG); win.geometry("520x520")
        ttk.Label(win,text="Send a friend request").pack(anchor="w",padx=14,pady=(14,2)); entry=ttk.Entry(win); entry.pack(fill="x",padx=14)
        def send():
            try: friend_service.send_request(self.user["id"],entry.get()); messagebox.showinfo("Friends","Request sent.",parent=win); win.destroy(); self.friends()
            except Exception as e: messagebox.showerror("Friends",str(e),parent=win)
        ttk.Button(win,text="Send",command=send).pack(anchor="w",padx=14,pady=6)
        ttk.Label(win,text="Incoming requests").pack(anchor="w",padx=14,pady=(12,3))
        for req in incoming:
            row=ttk.Frame(win); row.pack(fill="x",padx=14,pady=2); ttk.Label(row,text=req["display_name"]).pack(side="left")
            def respond(yes,ident=req["id"]):
                try: friend_service.respond(self.user["id"],ident,yes); win.destroy(); self.friends()
                except Exception as e: messagebox.showerror("Friends",str(e),parent=win)
            ttk.Button(row,text="Accept",command=lambda cb=respond:cb(True)).pack(side="right",padx=3); ttk.Button(row,text="Reject",command=lambda cb=respond:cb(False)).pack(side="right",padx=3)
        ttk.Label(win,text="Your friends").pack(anchor="w",padx=14,pady=(12,3))
        for friend in friends: ttk.Label(win,text=f"{friend['display_name']} (@{friend['username']})").pack(anchor="w",padx=14,pady=2)
        for friend in outgoing: ttk.Label(win,text=f"Request pending: {friend['display_name']}").pack(anchor="w",padx=14,pady=2)
    def logout(self): self.user=None; self.show_login()
