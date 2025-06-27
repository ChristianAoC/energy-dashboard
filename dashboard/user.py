from flask import request, current_app
import dashboard.mail as mail
import os
import re
import random
import json
import uuid
from datetime import datetime

users_file = "users.json"

# get current user from JSON DB
def get_user(email = None):
    if email == None:
        try:
            cookies = request.cookies
            email = cookies["Email"]
        except:
            return False

    if not os.path.isfile(users_file):
        return False
    with open(users_file, "r", encoding="utf-8", errors="replace") as f:
        users = json.load(f)
    for u in users:
        if "email" in u and u["email"] == email:
            return u
    return False

# get user level - used to check access level
def get_user_level(email, sessionid):
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
# login - update the login counter
def update_user(u, login=False):
    # minimum requirement - user element has an email, else throw
    if "email" not in u:
        return False

    if not os.path.isfile(users_file):
        with open(users_file, "w", encoding="utf-8") as f:
            f.write("[]")

    try:
        with open(users_file, "r", encoding="utf-8", errors="replace") as f:
            users = json.load(f)
        found = False
        for i, user in enumerate(users):
            if "email" in u and user["email"] == u["email"]:
                found = True
                for key in u:
                    user[key] = u[key]
                if login == True:
                    u["logincount"] = u["logincount"] + 1
                users[i] = u

        # user not found, add new and return
        if not found:
            u["logincount"] = 0
            users.append(u)
    except:
        return False

    tempfile = os.path.join(os.path.dirname(users_file), str(uuid.uuid4()))
    try:
        with open(tempfile, 'w') as outfile:
            json.dump(users, outfile, indent=4)
        try:
            os.replace(tempfile, users_file)
        except Exception as e:
            return False
    except Exception as e:
        return False
    return users

# login request or add user to JSON if not exist already
def login_request(email):
    if len(email.split('@')) < 2:
        return "Invalid email"
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
                return "Could not generate demo user."
            return [True, email, sessionID, "Demo user "+email.split('@')[0]+" created and logged in, refresh page!"]

    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        return "Email entered doesn't seem to be a valid address!"
    
    required_domains = []
    raw_required = current_app.config["REQUIRED_EMAIL_DOMAINS"]
    if raw_required:
        required_domains = [x.strip() for x in raw_required.split(",")]
    if len(required_domains) != 0 and email.split('@')[1] not in required_domains:
        return "Email needs to have one of those domains: "+", ".join(required_domains)

    u = get_user(email)
    code = random.randrange(100000,999999)

    # user not in DB, create new
    if (u == False):
        u = {
            "email": email,
            "level": current_app.config["DEFAULT_USER_LEVEL"]
        }

    u["code"] = code
    u["codetime"] = datetime.today().timestamp()
    added = update_user(u)
    if not added:
        return "Could not generate a login token for this user."
    else:
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
            return "Login token generated, check your mail."
        else:
            print("Mail sending off until everything else works. Post this URL into the browser:")
            print(codeurl)
            return "Email module is currently turned off, ask an admin to manually activate your account.<br><br>For admins: You need to set the SMTP .env variables to enable confirmation emails."

def check_code(email, code):
    u = get_user(email)
    if "code" in u:
        if u["code"] == int(code):
            if "codetime" in u:
                if datetime.today().timestamp() - u["codetime"] < 3600:
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
                    return (True, sessionid)
                else:
                    u.pop("code")
                    u.pop("codetime")
                    update_user(u)
                    return (False, "Code outdated. Generate a new login token!")
            else:
                u.pop("code")
                update_user(u)
                return (False, "Code found, but no timestamp. Generate a new login token.")
        else:
            return (False, "Wrong code. Did you click the right link?")
    else:
        return (False, "No code found. Generate a new login token.")

def delete_user(email):
    tbd = True

def list_users():
    try:
        with open(users_file, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except:
        return []
