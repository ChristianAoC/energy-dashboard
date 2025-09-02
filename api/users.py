from flask import request, current_app, Response, make_response, render_template, g

import datetime as dt
import random
import re
import uuid

import dashboard.mail as mail
from database import db
import log
import models


def get_user(email: str|None = None) -> models.User|None:
    if email is None:
        return None
    
    return db.session.execute(db.select(models.User).where(models.User.email == email)).scalar_one_or_none()

# Get user info for settings.json (get any user info just by email)
def get_user_info(email: str|None = None) -> dict|None:
    if email is None:
        try:
            cookies = request.cookies
            email = cookies["Email"]
        except:
            return None
    
    user = get_user(email)
    if user is not None:
        return {
            "email": user.email,
            "level": user.level
        }

def get_logged_in_user() -> dict | None:
    """Get currently logged-in user from session cookies if valid, else None."""
    cookies = request.cookies
    email = cookies.get("Email")
    sessionID = cookies.get("SessionID")

    if not email or not sessionID:
        return None

    # Assuming users.get_user_level(email, sessionID) returns 0 or None if invalid
    user_level = get_user_level(email, sessionID)
    if not user_level or user_level == 0:
        return None

    # Get user info (email and level)
    user_info = get_user_info(email)
    if user_info is None:
        return None

    # Confirm level matches session-validated level
    user_info['level'] = user_level
    return user_info

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
    
    update_session(email, session_id, dt.datetime.now().replace(second=0, microsecond=0))
    
    return user.level

def is_admin(user: models.User|None = None) -> bool:
    # Import here to stop circular import issue
    from api.users import get_user_level
    try:
        # Run all internal calls at admin level
        if (request.remote_addr in ['127.0.0.1', '::1'] and
                request.headers.get("Authorization") == current_app.config["internal_api_key"]):
            print("Bypassed admin level check for internal call")
            log.write(msg="Bypassed user level authorization for internal call", level=log.info)
            return True
        
        required_level = g.settings["USER_LEVEL_ADMIN"]
        
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

def set_cookies(email: str, sessionID: str, message: str|None = None, status: str = "info") -> Response:
    user = get_logged_in_user()
    resp = make_response(render_template('settings.html', user=user, message=message, status=status))
    resp.set_cookie("SessionID", sessionID, 60*60*24*365)
    resp.set_cookie("Email", email, 60*60*24*365)
    resp.status_code = 200
    return resp

def update_session(email: str, session_id: str, new_timestamp: dt.datetime):
    session = db.session.execute(
        db.select(models.Sessions)
        .where(models.Sessions.email == email)
        .where(models.Sessions.id == session_id)
    ).scalar_one_or_none()
    
    if session is not None:
        session.last_seen = new_timestamp
        db.session.commit()
        return
    
    new_session = models.Sessions(session_id, email, new_timestamp)
    db.session.add(new_session)
    db.session.commit()

def delete_session(email: str, session_id: str):
    session = db.session.execute(
        db.select(models.Sessions)
        .where(models.Sessions.email == email)
        .where(models.Sessions.id == session_id)
    ).scalar_one_or_none()
    
    if session is None:
        return
    
    db.session.delete(session)
    db.session.commit()

def set_level(email: str, level: int) -> bool:
    if email is None:
        return False

    if not user_exists(email):
        return False
    
    user = get_user(email)
    if user is None:
        return False
    
    user.level = level
    db.session.commit()
    return True

# save/update user entry in DB
# login - update the login counter (when admin changes settings, this is false)
def create_user(email: str, level: int, timestamp: dt.datetime|None = None) -> bool:
    if email is None:
        return False

    if user_exists(email):
        return False
    
    new_user = models.User(email=email, level=level)
    db.session.add(new_user)
    db.session.commit()
    return True

# login request or add user to JSON if not exist already
def login_request(email: str) -> tuple:
    if len(email) > 254 or len(email.split('@')) < 2:
        return ("Invalid email", 400)
    
    email_domain = email.split('@')[1]
    demo_user = False
    
    if (raw_demo := g.settings.get("DEMO_EMAIL_DOMAINS")) is not None:
        demo_domains = []
        if raw_demo:
            demo_domains = [x.strip() for x in raw_demo.split(",")]
        
        if len(demo_domains) != 0 and email_domain in demo_domains:
            demo_user = True
    
    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email) and not demo_user:
        return ("Email entered doesn't seem to be a valid address!", 400)
    
    required_domains = []
    if (raw_required := g.settings.get("REQUIRED_EMAIL_DOMAINS")) and not demo_user:
        required_domains = [x.strip() for x in raw_required.split(",")]
    
    if len(required_domains) != 0 and email_domain not in required_domains and not demo_user:
        return ("Email needs to have one of those domains: "+", ".join(required_domains), 400)
    
    first_user = False
    if not user_exists(email):
        level = g.settings["DEFAULT_USER_LEVEL"]
        # first user becomes admin!
        if len(list_users()) == 0:
            level = g.settings["USER_LEVEL_ADMIN"]
            first_user = True
        
        added = create_user(email, level)
        
        if not added:
            return ("Could not generate a login token for this user.", 500)
    
    code = str(random.randrange(100000,999999))
    code_time = dt.datetime.now().replace(second=0, microsecond=0)

    login_code = models.LoginCode(email, code, code_time)
    db.session.add(login_code)
    db.session.commit()
    
    codeurl  = str(request.url_root)
    codeurl += "api/user/verify?email=" + email
    codeurl += "&code=" + code

    if demo_user:
        return ("Demo user created. <a href='" + codeurl + "'>Click on this link</a> to activate.", 200)        

    if g.settings["SMTP_ENABLED"]:
        mailtext  = "You requested a login token for:\t\n\t\n"
        mailtext += g.settings["SITE_NAME"] + "\t\n\t\n"
        mailtext += "Copy/paste the following URL into your browser:\t\n\t\n"
        mailtext += codeurl + "\t\n\t\n"
        mailtext += "This code is valid for one hour."

        mailhtml = "<html><head></head><body>" + mailtext + "</body></html>"
        mailhtml = mailhtml.replace("Copy/paste", "<a href='"+codeurl+"' target='_blank'>Click here</a> or copy/paste", )
        mailhtml = mailhtml.replace("\n", "<br>", )
        
        mail.send_email(email, f"{g.settings['SITE_NAME']} Access Code", mailtext, mailhtml)
        return ("Login token generated, check your mail.", 200)

    if first_user:
        return ("First user created. <a href='" + codeurl + "'>Click on this link</a> to activate the admin.", 200)        
    print("Mail sending off until everything else works. Post this URL into the browser:")
    print(codeurl)
    log.write(msg="Mail sending is off", extra_info=f"For user {email}", level=log.info)
    return ("Email module is currently turned off, ask an admin to manually activate your account.<br><br>For admins: You need to set the SMTP .env variables to enable confirmation emails.", 200)

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
    
    if (dt.datetime.now().replace(second=0, microsecond=0) - code_record.timestamp).seconds >= 3600:
        db.session.delete(code_record)
        db.session.commit()
        return (False, "Code outdated. Generate a new login token!")

    sessionid = str(uuid.uuid4())
    timestamp = dt.datetime.now().replace(second=0, microsecond=0)
    update_session(email, sessionid, timestamp)
    
    code_record.user.login(timestamp)
    
    # Invalidate other codes
    db.session.execute(db.delete(models.LoginCode).where(models.LoginCode.email == email))
    db.session.commit()
    
    return (True, sessionid)

def delete_user(email: str) -> bool:
    if not email:
        return False

    if not user_exists(email):
        return True
    
    user = get_user(email)
    if user is None:
        return True
    
    if is_admin(user):
        return False
    
    db.session.delete(user)
    db.session.commit()
    return True

def list_users() -> list:
    return [x.to_dict() for x in db.session.execute(db.select(models.User)).scalars().all()]