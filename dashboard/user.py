from flask import request, current_app
import dashboard.mail as mail
import os
import re
import random
import json
import uuid
import time
from datetime import datetime

users_file = "data/users.json"

# lock file functions to make sure no concurrent changes lead to data loss
def acquire_lock(lockfile: str, timeout: int = 5) -> bool:
    start = time.time()
    while True:
        try:
            fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            return True
        except FileExistsError:
            if time.time() - start > timeout:
                return False
            time.sleep(0.01)  # wait and retry

def release_lock(lockfile: str) -> None:
    try:
        os.remove(lockfile)
    except FileNotFoundError:
        pass

# get current user from JSON DB
def get_user(email: str|None = None) -> dict|None:
    if email == None:
        try:
            cookies = request.cookies
            email = cookies["Email"]
        except:
            return None

    if not os.path.isfile(users_file):
        return None
    
    with open(users_file, "r", encoding="utf-8", errors="replace") as f:
        users = json.load(f)
    
    for u in users:
        if "email" in u and u["email"] == email:
            return u
    return None

# get user level - used to check access level
def get_user_level(email: str, sessionid: str) -> int:
    if os.path.isfile(users_file):
        with open(users_file, "r", encoding="utf-8", errors="replace") as f:
            users = json.load(f)
        for u in users:
            if "email" in u and u["email"] == email and "sessions" in u:
                for i, s in enumerate(u["sessions"]):
                    if s["id"] == sessionid:
                        if s["lastseen"] != datetime.now().strftime("%Y-%m-%d"):
                            s["lastseen"] = datetime.now().strftime("%Y-%m-%d")
                            u["sessions"][i] = s
                            update_user(u)
                        return int(u["level"])
    return 0

# save/update user entry in DB
# login - update the login counter (when admin changes settings, this is false)
def update_user(u: dict, login: bool = False) -> bool:
    if "email" not in u:
        return False

    lock_file = users_file + ".lock"

    # Ensure users file exists
    if not os.path.isfile(users_file):
        with open(users_file, "w", encoding="utf-8") as f:
            f.write("[]")

    if not acquire_lock(lock_file, timeout=5):
        print("Could not acquire lock.")
        return False

    try:
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)

        found = False
        for i, user in enumerate(users):
            if user.get("email") == u["email"]:
                if login:
                    u["logincount"] = user.get("logincount", 0) + 1
                else:
                    u["logincount"] = u.get("logincount", user.get("logincount", 0))
                users[i] = u
                found = True
                break

        if not found:
            u["logincount"] = 0
            users.append(u)

        # Write to temp file and atomically replace
        tempfile = os.path.join(os.path.dirname(users_file), str(uuid.uuid4()))
        with open(tempfile, "w", encoding="utf-8") as tmp:
            json.dump(users, tmp, indent=4)
        os.replace(tempfile, users_file)

        return True

    except Exception as e:
        print("Error updating user:", e)
        return False

    finally:
        release_lock(lock_file)

# login request or add user to JSON if not exist already
def login_request(email: str) -> tuple:
    if len(email.split('@')) < 2:
        return ("Invalid email", 400)
    
    if current_app.config["DEMO_EMAIL_DOMAINS"] != None:
        demo_domains = []
        raw_demo = current_app.config["DEMO_EMAIL_DOMAINS"]
        if raw_demo:
            demo_domains = [x.strip() for x in raw_demo.split(",")]
        if len(demo_domains) != 0 and email.split('@')[1] in demo_domains:
            sessionID = str(uuid.uuid4())
            u = {
                "email": email,
                "level": current_app.config["DEFAULT_USER_LEVEL"],
                "lastlogin": datetime.now().strftime("%Y-%m-%d"),
                "sessions": [{
                    "id": sessionID,
                    "lastseen": datetime.now().strftime("%Y-%m-%d")
                }]
            }
            added = update_user(u)
            if not added:
                return ("Could not generate demo user.", 500)
            return ([True, email, sessionID, "Demo user "+email.split('@')[0]+" created and logged in, refresh page!"], 200)

    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        return ("Email entered doesn't seem to be a valid address!", 400)
    
    required_domains = []
    raw_required = current_app.config["REQUIRED_EMAIL_DOMAINS"]
    if raw_required:
        required_domains = [x.strip() for x in raw_required.split(",")]
    if len(required_domains) != 0 and email.split('@')[1] not in required_domains:
        return ("Email needs to have one of those domains: "+", ".join(required_domains), 400)

    u = get_user(email)
    code = random.randrange(100000,999999)

    # user not in DB, create new
    if (u is None):
        u = {
            "email": email,
            "level": current_app.config["DEFAULT_USER_LEVEL"]
        }
        # first user becomes admin!
        if len(list_users()) == 0:
            u["level"] = 5

    u["code"] = code
    u["codetime"] = datetime.today().timestamp()
    added = update_user(u)
    if not added:
        return ("Could not generate a login token for this user.", 500)

    codeurl  = str(request.url_root)
    codeurl += "verify_login?email=" + email
    codeurl += "&code=" + str(code)

    mailtext  = "You requested a login token for:\t\n\t\n"
    mailtext += current_app.config["SITE_NAME"] + "\t\n\t\n"
    mailtext += "Copy/paste the following URL into your browser:\t\n\t\n"
    mailtext += codeurl + "\t\n\t\n"
    mailtext += "This code is valid for one hour."

    mailhtml = "<html><head></head><body>" + mailtext + "</body></html>"
    mailhtml = mailhtml.replace("Copy/paste", "<a href='"+codeurl+"' target='_blank'>Click here</a> or copy/paste", )
    mailhtml = mailhtml.replace("\n", "<br>", )

    if current_app.config["SMTP_ENABLED"]:
        mail.send_email(email, current_app.config["SITE_NAME"]+" Access Code", mailtext, mailhtml)
        return ("Login token generated, check your mail.", 200)

    print("Mail sending off until everything else works. Post this URL into the browser:")
    print(codeurl)
    return ("Email module is currently turned off, ask an admin to manually activate your account.<br><br>For admins: You need to set the SMTP .env variables to enable confirmation emails.", 503)

def check_code(email: str, code: str) -> tuple:
    u = get_user(email)
    
    if u is None:
        return (False, "User doesn't exist. Generate a new login token")
    
    if "code" not in u:
        return (False, "No code found. Generate a new login token.")
    
    if u["code"] != int(code):
        return (False, "Wrong code. Did you click the right link?")
    
    if "codetime" not in u:
        u.pop("code")
        update_user(u)
        return (False, "Code found, but no timestamp. Generate a new login token.")
    
    if datetime.today().timestamp() - u["codetime"] >= 3600:
        u.pop("code")
        u.pop("codetime")
        update_user(u)
        print("success2")
        print(u)
        return (False, "Code outdated. Generate a new login token!")

    u.pop("code")
    u.pop("codetime")
    sessionid = str(uuid.uuid4())
    u["lastlogin"] = datetime.now().strftime("%Y-%m-%d")
    session = {
        "id": sessionid,
        "lastseen": datetime.now().strftime("%Y-%m-%d")
    }
    if "sessions" not in u:
        u["sessions"] = []
    u["sessions"].append(session)
    update_user(u, True)
    print("success")
    print(u)
    return (True, sessionid)

def delete_user(email: str) -> bool:
    if not email:
        return False

    lock_file = users_file + ".lock"

    if not os.path.isfile(users_file):
        return False

    if not acquire_lock(lock_file, timeout=5):
        print("Could not acquire lock.")
        return False

    try:
        with open(users_file, "r", encoding="utf-8", errors="replace") as f:
            users = json.load(f)

        new_users = [user for user in users if user.get("email") != email]

        if len(new_users) == len(users):
            # No user found to delete
            return False

        tempfile = os.path.join(os.path.dirname(users_file), str(uuid.uuid4()))
        with open(tempfile, "w", encoding="utf-8", errors="replace") as tmp:
            json.dump(new_users, tmp, indent=4)
        os.replace(tempfile, users_file)

        return True

    except Exception as e:
        print("Error deleting user:", e)
        return False

    finally:
        release_lock(lock_file)

def list_users() -> list:
    try:
        with open(users_file, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except:
        return []
