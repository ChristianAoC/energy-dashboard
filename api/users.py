from flask import request, current_app

import datetime as dt
import random
import re
import uuid

import dashboard.mail as mail
from database import db
import models


def get_user(email: str|None = None) -> models.User|None:
    if email == None:
        try:
            cookies = request.cookies
            email = cookies["Email"]
        except:
            return None
    
    return db.session.execute(db.select(models.User).where(models.User.email == email)).scalar_one_or_none()

# get current user from JSON DB
def get_user_dict(email: str|None = None) -> dict|None:
    user = get_user(email)
    if user is None:
        return
    
    return user.to_dict()

def user_exists(email: str) -> bool:
    if email is None:
        return False

    existing_user = db.session.execute(db.select(models.User).where(models.User.email == email)).scalar_one_or_none()
    if existing_user is None:
        return False
    
    return True

# get user level - used to check access level
def get_user_level(email: str|None, session_id: str|None) -> int:
    if email is None or session_id is None:
        return 0
    
    if not user_exists(email):
        return 0

    user = db.session.execute(
        db.select(models.User)
        .join(models.Sessions)
        .where(models.User.email == email)
        .where(models.Sessions.id == session_id)
    ).scalar_one_or_none()
    
    if user is None:
        return 0
    
    update_session(email, session_id, dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    
    return user.level

def is_admin(user: models.User|None = None) -> bool:
    # Import here to stop circular import issue
    from api.users import get_user_level
    try:
        # Run all internal calls at admin level
        if request.remote_addr in ['127.0.0.1', '::1'] and request.headers.get("Authorization") == current_app.config["internal_api_key"]:
            print("Bypassed admin level check for internal call")
            return True
        
        required_level = int(current_app.config["USER_LEVEL_ADMIN"])
        
        cookies = request.cookies
        email = cookies.get("Email", None)
        sessionID = cookies.get("SessionID", None)
        
        if user is None:
            user_level = get_user_level(email, sessionID)
        else:
            user_level = user.level
        
        if user_level < required_level:
            return False
    except:
        return False
    return True

def update_session(email: str, session_id: str, timestamp: dt.datetime):
    session = db.session.execute(
        db.select(models.Sessions)
        .where(models.Sessions.email == email)
        .where(models.Sessions.id == session_id)
    ).scalar_one_or_none()
    
    if session is not None:
        session.last_seen = timestamp
        db.session.commit()
        return
    
    new_session = models.Sessions(session_id, email, timestamp)
    db.session.add(new_session)
    db.session.commit()

# save/update user entry in DB
# login - update the login counter (when admin changes settings, this is false)
def update_user(u: dict, login: bool = False) -> bool:
    if "email" not in u:
        return False

    if not user_exists(email):
        return False
    
    user = get_user(email)
    if user is None:
        login_count = 0
        if login:
            login_count += 1
        new_user = models.User(email=u["email"], level=u["level"], last_login=None, login_count=login_count)
        db.session.add(new_user)
        db.session.commit()
        return True
    
    login_count = u.get("login_count")
    if type(login_count) is int:
        login_count += 1
    
    user.update(level=u.get("level"), last_login=u.get("lastlogin"), login_count=login_count)
    db.session.commit()
    return True

# login request or add user to JSON if not exist already
def login_request(email: str) -> tuple:
    if len(email) > 254 or len(email.split('@')) < 2:
        return ("Invalid email", 400)
    
    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        return ("Email entered doesn't seem to be a valid address!", 400)
    
    email_domain = email.split('@')[1]
    
    if current_app.config["DEMO_EMAIL_DOMAINS"] != None:
        demo_domains = []
        raw_demo = current_app.config["DEMO_EMAIL_DOMAINS"]
        if raw_demo:
            demo_domains = [x.strip() for x in raw_demo.split(",")]
        
        if len(demo_domains) != 0 and email_domain in demo_domains:
            sessionID = str(uuid.uuid4())
            timestamp = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            u = {
                "email": email,
                "level": current_app.config["DEFAULT_USER_LEVEL"],
                "lastlogin": timestamp,
            }
            added = update_user(u)
            if not added:
                added = update_session(email, sessionID, timestamp)
            
            if not added:
                return ("Could not generate demo user.", 400)
            return ((email, sessionID), 200)
    
    required_domains = []
    raw_required = current_app.config["REQUIRED_EMAIL_DOMAINS"]
    if raw_required:
        required_domains = [x.strip() for x in raw_required.split(",")]
    
    if len(required_domains) != 0 and email_domain not in required_domains:
        return ("Email needs to have one of those domains: "+", ".join(required_domains), 400)

    u = get_user_dict(email)
    
    # user not in DB, create new
    if u is None:
        u = {
            "email": email,
            "level": current_app.config["DEFAULT_USER_LEVEL"]
        }
        # first user becomes admin!
        if len(list_users()) == 0:
            u["level"] = 5
    
    added = update_user(u)
    if not added:
        return ("Could not generate a login token for this user.", 500)
    
    code = str(random.randrange(100000,999999))
    code_time = dt.datetime.now()

    login_code = models.LoginCode(email, code, code_time)
    db.session.add(login_code)
    db.session.commit()
    
    codeurl  = str(request.url_root)
    codeurl += "api/user/verify?email=" + email
    codeurl += "&code=" + code

    if current_app.config["SMTP_ENABLED"]:
        mailtext  = "You requested a login token for:\t\n\t\n"
        mailtext += current_app.config["SITE_NAME"] + "\t\n\t\n"
        mailtext += "Copy/paste the following URL into your browser:\t\n\t\n"
        mailtext += codeurl + "\t\n\t\n"
        mailtext += "This code is valid for one hour."

        mailhtml = "<html><head></head><body>" + mailtext + "</body></html>"
        mailhtml = mailhtml.replace("Copy/paste", "<a href='"+codeurl+"' target='_blank'>Click here</a> or copy/paste", )
        mailhtml = mailhtml.replace("\n", "<br>", )
        
        mail.send_email(email, current_app.config["SITE_NAME"]+" Access Code", mailtext, mailhtml)
        return ("Login token generated, check your mail.", 200)

    print("Mail sending off until everything else works. Post this URL into the browser:")
    print(codeurl)
    return ("Email module is currently turned off, ask an admin to manually activate your account.<br><br>For admins: You need to set the SMTP .env variables to enable confirmation emails.", 503)

def check_code(email: str, code: str) -> tuple:
    if not user_exists(email):
        return (False, "User doesn't exist. Generate a new login token")
    
    code_record = db.session.execute(
        db.select(models.LoginCode)
        .where(models.LoginCode.email == email)
        .where(models.LoginCode.code == code)
    ).scalar_one_or_none()
    
    if code_record is None:
        return (False, "No code found. Generate a new login token.")
    
    if (dt.datetime.now() - code_record.timestamp).seconds >= 3600:
        db.session.delete(code_record)
        db.session.commit()
        return (False, "Code outdated. Generate a new login token!")

    sessionid = str(uuid.uuid4())
    timestamp = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    update_session(email, sessionid, timestamp)
    
    db.session.delete(code_record)
    db.session.commit()
    
    return (True, sessionid)

def delete_user(email: str) -> bool:
    if not email:
        return False

    if not user_exists(email):
        return True
    
    user = get_user(email)
    if user is not None:
        return False
    
    db.session.delete(user)
    db.session.commit()
    return True

def list_users() -> list:
    return [x.to_dict() for x in db.session.execute(db.select(models.User)).scalars().all()]