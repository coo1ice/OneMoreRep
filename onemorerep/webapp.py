"""FastAPI application backing the OneMoreRep website."""
from contextlib import asynccontextmanager
from datetime import date, time
import logging
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError

import config
from onemorerep import auth
from onemorerep.database import connect, initialize_schema, transaction
from onemorerep.services import achievement_service, admin_service, friend_service, leaderboard_service, media_service, report_service
from onemorerep.services.web_service import (
    add_post_comment, change_post_like, create_feed_post, end_session, get_feed,
    get_feed_image, list_post_comments, new_session, session_user,
)
from onemorerep.services.workout_service import save_activity

logger=logging.getLogger("onemorerep.web")
MAX_IMAGE_BYTES=8*1024*1024
IMAGE_TYPES={
    "image/jpeg": lambda b:b.startswith(b"\xff\xd8\xff"),
    "image/png": lambda b:b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda b:len(b)>=12 and b[:4]==b"RIFF" and b[8:12]==b"WEBP",
}


@asynccontextmanager
async def lifespan(_app):
    if config.MEDIA_STORAGE == "local":
        config.UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    initialize_schema()
    yield


app=FastAPI(title="OneMoreRep API",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=config.CORS_ORIGINS,
                   allow_credentials=True,allow_methods=["GET","POST","DELETE","OPTIONS"],
                   allow_headers=["Content-Type"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def check_mutation_origin(request:Request,call_next):
    if request.method in {"POST","PUT","PATCH","DELETE"}:
        origin=request.headers.get("origin")
        if origin:
            parsed_origin=urlsplit(origin)
            request_host=request.headers.get("host","").lower()
            same_origin=(parsed_origin.scheme==request.url.scheme and
                         parsed_origin.netloc.lower()==request_host and
                         not parsed_origin.path and not parsed_origin.query and not parsed_origin.fragment)
            if not same_origin and origin not in config.CORS_ORIGINS:
                return JSONResponse(status_code=403,content={"detail":"Request origin is not allowed."})
    return await call_next(request)


@app.exception_handler(Exception)
async def safe_server_error(_request,exc):
    logger.exception("Unhandled OneMoreRep API error",exc_info=exc)
    return JSONResponse(status_code=500,content={"detail":"The request could not be completed."})


class RegisterIn(BaseModel):
    username:str=Field(min_length=3,max_length=40)
    password:str=Field(min_length=8,max_length=72)
    display_name:str=Field(min_length=1,max_length=80)

class LoginIn(BaseModel):
    username:str=Field(min_length=1,max_length=40)
    password:str=Field(min_length=1,max_length=72)

class FriendRequestIn(BaseModel):
    username:str=Field(min_length=1,max_length=40)

class FriendResponseIn(BaseModel):
    accept:bool

class CommentIn(BaseModel):
    body:str=Field(min_length=1,max_length=500)

class AdminMemberUpdate(BaseModel):
    display_name:str=Field(min_length=1,max_length=80)

class AdminProgressUpdate(BaseModel):
    weight_kg:float=Field(gt=0,le=500)
    notes:str=Field(default="",max_length=1000)

class AdminPostUpdate(BaseModel):
    caption:str=Field(default="",max_length=500)

class ExerciseIn(BaseModel):
    exercise_name:str=Field(min_length=1,max_length=120)
    weight:float=Field(ge=0)
    reps:int=Field(gt=0)
    sets:int=Field(gt=0)

class WalkingIn(BaseModel):
    distance:float=Field(ge=0)
    steps:int=Field(ge=0)
    calories:float=Field(ge=0)
    avg_speed:float=Field(ge=0)

class SportIn(BaseModel):
    sport_name:str=Field(min_length=1,max_length=80)

class AdminWorkoutUpdate(BaseModel):
    notes:str|None=Field(default=None,max_length=1000)
    exercises:list[ExerciseIn]|None=None
    walking:WalkingIn|None=None
    sport_name:str|None=Field(default=None,max_length=80)

class ActivityIn(BaseModel):
    kind:Literal["Strength","Walking","Sports"]
    activity_date:date
    start_time:time
    end_time:time
    notes:str=Field(default="",max_length=1000)
    exercises:list[ExerciseIn]=Field(default_factory=list,max_length=40)
    walking:WalkingIn|None=None
    sport:SportIn|None=None


def current_user(request:Request):
    user=session_user(request.cookies.get(config.SESSION_COOKIE_NAME))
    if not user: raise HTTPException(status_code=401,detail="Sign in to continue.")
    return user


def admin_user(user:Annotated[dict,Depends(current_user)]):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403,detail="Administrator access is required.")
    return user


def _set_session(response:Response,token):
    response.set_cookie(config.SESSION_COOKIE_NAME,token,max_age=30*24*60*60,
        httponly=True,secure=config.SESSION_COOKIE_SECURE,samesite="lax",path="/")


def _clear_session(response:Response):
    response.delete_cookie(config.SESSION_COOKIE_NAME,path="/",secure=config.SESSION_COOKIE_SECURE,
                           httponly=True,samesite="lax")


async def _read_image(upload):
    if not upload or not getattr(upload,"filename",None):
        return None,None
    image_bytes=await upload.read(MAX_IMAGE_BYTES+1)
    if len(image_bytes)>MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413,detail="Images must be 8 MB or smaller.")
    mime_type=next((kind for kind,valid in IMAGE_TYPES.items() if valid(image_bytes)),None)
    if not mime_type:
        raise HTTPException(status_code=415,detail="Use a JPEG, PNG, or WebP image.")
    return image_bytes,mime_type


@app.get("/api/health")
def health():
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status":"ok"}


@app.post("/api/auth/register",status_code=201)
def register(payload:RegisterIn,response:Response):
    try:
        user_id=auth.register(payload.username,payload.password,payload.display_name)
        user={"id":user_id,"username":payload.username.strip(),"display_name":payload.display_name.strip(),"role":"user"}
        token=new_session(user_id)
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
    except Exception: raise
    _set_session(response,token)
    return user


@app.post("/api/auth/login")
def login(payload:LoginIn,response:Response):
    user=auth.login(payload.username,payload.password)
    if not user: raise HTTPException(status_code=401,detail="Username or password is incorrect.")
    _set_session(response,new_session(user["id"]))
    return user


@app.post("/api/auth/logout",status_code=204)
def logout(request:Request,response:Response):
    end_session(request.cookies.get(config.SESSION_COOKIE_NAME))
    _clear_session(response)
    response.status_code=204
    return response


@app.get("/api/me")
def me(user:Annotated[dict,Depends(current_user)]):
    return user


@app.get("/api/admin/users")
def admin_users(_admin:Annotated[dict,Depends(admin_user)]):
    return admin_service.list_users()


@app.get("/api/admin/users/{user_id}")
def admin_user_report(user_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    result=admin_service.user_report(user_id)
    if not result: raise HTTPException(status_code=404,detail="Account not found.")
    return result


@app.put("/api/admin/users/{user_id}")
def update_admin_member(user_id:int,payload:AdminMemberUpdate,_admin:Annotated[dict,Depends(admin_user)]):
    result=admin_service.update_member(user_id,payload.display_name)
    if not result: raise HTTPException(status_code=404,detail="Account not found.")
    return result


@app.delete("/api/admin/users/{user_id}")
def delete_admin_member(user_id:int,admin:Annotated[dict,Depends(admin_user)]):
    try: deleted=admin_service.delete_member(user_id,admin["id"])
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
    if not deleted: raise HTTPException(status_code=404,detail="Account not found.")
    return {"deleted":True}


@app.put("/api/admin/users/{user_id}/workouts/{workout_id}")
def update_admin_workout(user_id:int,workout_id:int,payload:AdminWorkoutUpdate,_admin:Annotated[dict,Depends(admin_user)]):
    try:
        updated=admin_service.update_workout(user_id,workout_id,payload.notes,
            payload.exercises,
            payload.walking,payload.sport_name)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not updated: raise HTTPException(status_code=404,detail="Workout not found.")
    return {"updated":True}


@app.delete("/api/admin/users/{user_id}/workouts/{workout_id}")
def delete_admin_workout(user_id:int,workout_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    if not admin_service.delete_workout(user_id,workout_id): raise HTTPException(status_code=404,detail="Workout not found.")
    return {"deleted":True}


@app.put("/api/admin/users/{user_id}/progress/{report_id}")
def update_admin_progress(user_id:int,report_id:int,payload:AdminProgressUpdate,_admin:Annotated[dict,Depends(admin_user)]):
    try: updated=admin_service.update_progress(user_id,report_id,payload.weight_kg,payload.notes)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not updated: raise HTTPException(status_code=404,detail="Progress report not found.")
    return {"updated":True}


@app.delete("/api/admin/users/{user_id}/progress/{report_id}")
def delete_admin_progress(user_id:int,report_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    if not admin_service.delete_progress(user_id,report_id): raise HTTPException(status_code=404,detail="Progress report not found.")
    return {"deleted":True}


@app.put("/api/admin/users/{user_id}/posts/{post_id}")
def update_admin_post(user_id:int,post_id:int,payload:AdminPostUpdate,_admin:Annotated[dict,Depends(admin_user)]):
    try: updated=admin_service.update_post(user_id,post_id,payload.caption)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not updated: raise HTTPException(status_code=404,detail="Post not found.")
    return {"updated":True}


@app.delete("/api/admin/users/{user_id}/posts/{post_id}")
def delete_admin_post(user_id:int,post_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    if not admin_service.delete_post(user_id,post_id): raise HTTPException(status_code=404,detail="Post not found.")
    return {"deleted":True}


@app.delete("/api/admin/users/{user_id}/comments/{comment_id}")
def delete_admin_comment(user_id:int,comment_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    if not admin_service.delete_comment(user_id,comment_id): raise HTTPException(status_code=404,detail="Comment not found.")
    return {"deleted":True}


def _admin_image(item):
    if not item: raise HTTPException(status_code=404,detail="Image not found.")
    image,mime_type=item
    return Response(image,media_type=mime_type,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


@app.get("/api/admin/users/{user_id}/workouts/{workout_id}/image")
def admin_workout_image(user_id:int,workout_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    return _admin_image(admin_service.workout_image(user_id,workout_id))


@app.get("/api/admin/users/{user_id}/progress/{report_id}/image")
def admin_progress_image(user_id:int,report_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    return _admin_image(admin_service.progress_image(user_id,report_id))


@app.get("/api/admin/users/{user_id}/posts/{post_id}/image")
def admin_post_image(user_id:int,post_id:int,_admin:Annotated[dict,Depends(admin_user)]):
    return _admin_image(admin_service.post_image(user_id,post_id))


@app.get("/api/dashboard")
def dashboard(user:Annotated[dict,Depends(current_user)]):
    return report_service.dashboard(user["id"])


@app.get("/api/activities")
def activities(user:Annotated[dict,Depends(current_user)]):
    return report_service.history(user["id"])


@app.post("/api/activities",status_code=201)
async def create_activity(request:Request,user:Annotated[dict,Depends(current_user)]):
    image_bytes=None; image_mime=None
    try:
        if request.headers.get("content-type","").startswith("multipart/form-data"):
            form=await request.form()
            payload=ActivityIn.model_validate_json(str(form.get("activity","")))
            image_bytes,image_mime=await _read_image(form.get("workout_image"))
        else:
            payload=ActivityIn.model_validate(await request.json())
    except (ValidationError,ValueError) as exc:
        raise HTTPException(status_code=422,detail="Activity details are invalid.") from exc
    if payload.kind=="Strength" and not payload.exercises:
        raise HTTPException(status_code=422,detail="Add at least one exercise.")
    if payload.kind=="Walking" and payload.walking is None:
        raise HTTPException(status_code=422,detail="Walking distance and step details are required.")
    if payload.kind=="Sports" and payload.sport is None:
        raise HTTPException(status_code=422,detail="Enter the sport you played.")
    try:
        workout_id,exp_amount,duration=save_activity(
            user["id"],payload.kind,payload.activity_date,payload.start_time.strftime("%H:%M"),
            payload.end_time.strftime("%H:%M"),payload.notes,
            exercises=[item.model_dump() for item in payload.exercises],
            walking=payload.walking.model_dump() if payload.walking else None,
            sport_name=payload.sport.sport_name if payload.sport else None,
            workout_image_bytes=image_bytes,workout_image_mime=image_mime,
        )
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"id":workout_id,"exp_earned":exp_amount,"duration_seconds":duration}


@app.get("/api/activities/{workout_id}")
def activity_detail(workout_id:int,user:Annotated[dict,Depends(current_user)]):
    try: return friend_service.workout_detail(user["id"],workout_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail="Activity not found.") from exc


@app.get("/api/activities/{workout_id}/image")
def workout_image(workout_id:int,user:Annotated[dict,Depends(current_user)]):
    item=media_service.get_workout_image(user["id"],workout_id)
    if not item: raise HTTPException(status_code=404,detail="Workout image not found.")
    image,mime_type=item
    return Response(image,media_type=mime_type,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


@app.get("/api/progress")
def progress_reports(user:Annotated[dict,Depends(current_user)]):
    return media_service.list_progress_reports(user["id"])


@app.post("/api/progress",status_code=201)
async def save_progress(
    user:Annotated[dict,Depends(current_user)],
    report_date:Annotated[date,Form()],
    weight_kg:Annotated[float,Form(gt=0,le=500)],
    notes:Annotated[str,Form(max_length=1000)]="",
    photo:Annotated[UploadFile|None,File()]=None,
):
    image_bytes,image_mime=await _read_image(photo)
    try:
        report_id=media_service.save_progress_report(user["id"],report_date,weight_kg,notes,image_bytes,image_mime)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"id":report_id}


@app.get("/api/progress/{report_id}/image")
def progress_image(report_id:int,user:Annotated[dict,Depends(current_user)]):
    item=media_service.get_progress_image(user["id"],report_id)
    if not item: raise HTTPException(status_code=404,detail="Progress photo not found.")
    image,mime_type=item
    return Response(image,media_type=mime_type,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


@app.get("/api/exp")
def exp_history(user:Annotated[dict,Depends(current_user)]):
    return report_service.history(user["id"],exp_only=True)


@app.get("/api/leaderboard")
def leaderboard(user:Annotated[dict,Depends(current_user)]):
    with connect() as conn: rows=leaderboard_service.leaderboard(conn)
    return rows


@app.get("/api/statistics")
def statistics(user:Annotated[dict,Depends(current_user)]):
    return report_service.statistics(user["id"])


@app.get("/api/achievements")
def achievements(user:Annotated[dict,Depends(current_user)]):
    return achievement_service.list_achievements(user["id"])


@app.get("/api/friends")
def friends(user:Annotated[dict,Depends(current_user)]):
    incoming,outgoing,accepted=friend_service.requests_and_friends(user["id"])
    return {"incoming":incoming,"outgoing":outgoing,"friends":accepted}


@app.post("/api/friends/requests",status_code=201)
def send_friend_request(payload:FriendRequestIn,user:Annotated[dict,Depends(current_user)]):
    try: friend_service.send_request(user["id"],payload.username)
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
    return {"status":"pending"}


@app.post("/api/friends/requests/{friendship_id}")
def respond_friend_request(friendship_id:int,payload:FriendResponseIn,user:Annotated[dict,Depends(current_user)]):
    try: friend_service.respond(user["id"],friendship_id,payload.accept)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"status":"accepted" if payload.accept else "rejected"}


@app.get("/api/feed")
def feed(user:Annotated[dict,Depends(current_user)],limit:int=Query(default=30,ge=1,le=50),before_id:int|None=None):
    return get_feed(user["id"],limit,before_id)


@app.post("/api/feed",status_code=201)
async def share_to_feed(
    user:Annotated[dict,Depends(current_user)],
    caption:Annotated[str,Form(max_length=500)]="",
    workout_id:Annotated[int|None,Form()]=None,
    achievement_id:Annotated[int|None,Form()]=None,
    include_workout_image:Annotated[bool,Form()]=False,
    screenshot:Annotated[UploadFile|None,File()]=None,
):
    image_bytes,mime_type=await _read_image(screenshot)
    try:
        post_id=create_feed_post(user["id"],caption,workout_id,image_bytes,mime_type,
                                 achievement_id,include_workout_image)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"id":post_id}


@app.get("/api/feed/{post_id}/image")
def feed_image(post_id:int,user:Annotated[dict,Depends(current_user)]):
    item=get_feed_image(user["id"],post_id)
    if not item: raise HTTPException(status_code=404,detail="Screenshot not found.")
    image,mime_type=item
    return Response(image,media_type=mime_type,headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


@app.post("/api/feed/{post_id}/likes")
def like_feed_post(post_id:int,user:Annotated[dict,Depends(current_user)]):
    try: return change_post_like(user["id"],post_id,True)
    except ValueError as exc: raise HTTPException(status_code=404,detail="Post not found.") from exc


@app.delete("/api/feed/{post_id}/likes")
def unlike_feed_post(post_id:int,user:Annotated[dict,Depends(current_user)]):
    try: return change_post_like(user["id"],post_id,False)
    except ValueError as exc: raise HTTPException(status_code=404,detail="Post not found.") from exc


@app.get("/api/feed/{post_id}/comments")
def feed_comments(post_id:int,user:Annotated[dict,Depends(current_user)]):
    try: return list_post_comments(user["id"],post_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail="Post not found.") from exc


@app.post("/api/feed/{post_id}/comments",status_code=201)
def comment_on_feed_post(post_id:int,payload:CommentIn,user:Annotated[dict,Depends(current_user)]):
    try: return add_post_comment(user["id"],post_id,payload.body)
    except ValueError as exc:
        if str(exc)=="Post not found.": raise HTTPException(status_code=404,detail=str(exc)) from exc
        raise HTTPException(status_code=422,detail=str(exc)) from exc
