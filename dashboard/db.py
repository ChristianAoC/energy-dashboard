import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import dashboard.mail as mail
import os
import re
import random
from dotenv import load_dotenv

load_dotenv()
required_domains = []
if os.getenv("REQUIRED_EMAIL_DOMAINS") != None:
    required_domains = [x.strip() for x in os.getenv("REQUIRED_EMAIL_DOMAINS").split(',')]
sitename = os.getenv("SITE_NAME")

if not os.path.isfile('database.db'):
    conn = sqlite3.connect('database.db')
    if not os.path.isfile('SCHEMA-database.db.sql'):
        print("DB doesn't exist and SQLite schema file not found!")
    with open('SCHEMA-database.db.sql') as fp:
        conn.executescript(fp.read())

#rework like this:
#https://github.com/helloflask/flask-examples/blob/main/http/app.py#L136-L156

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_userid(username):
    conn = get_db_connection()
    res = conn.execute("SELECT id FROM user WHERE username=? COLLATE NOCASE",
                       (username, )).fetchone()
    conn.close()
    if not res:
        return False
    return res[0]

def check_login(username, password):
    conn = get_db_connection()
    if '@' in username:
        res = conn.execute("SELECT * FROM user WHERE email=? COLLATE NOCASE",
                        (username, )).fetchone()
    else:
        res = conn.execute("SELECT * FROM user WHERE username=? COLLATE NOCASE",
                        (username, )).fetchone()
    conn.close()
    if res:
        if (check_password_hash(res[2], password)):
            return res[0]
        else:
            print("Password didn't match")
    else:
        print("DB didn't return anything")
    return False

def change_password(username, old_pw, new_pw):
    if check_login(username, old_pw):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE user SET password=? WHERE username=? COLLATE NOCASE",
                        (generate_password_hash(new_pw), username))
        if cursor.rowcount == 1:
            conn.commit()
            conn.close()
            return "Password changed"
        else:
            conn.close()
            return "Password wasn't updated"
    return "Old password incorrect"

def add_user(username, password, email):
    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        return "Email entered doesn't seem to be a valid address!"
    if required_domains != None and email.split('@')[1] not in required_domains:
        return "Email needs to have one of those domains: "+", ".join(required_domains)
    if '@' in username:
        return "Username cannot contain the '@' symbol"
    conn = get_db_connection()
    if len(conn.execute("SELECT * FROM user WHERE username=? COLLATE NOCASE", (username, )).fetchall()) > 0:
        conn.close()
        return "Username exists already!"
    elif len(conn.execute("SELECT * FROM user WHERE email=? COLLATE NOCASE", (email, )).fetchall()) > 0:
        conn.close()
        return "Email already registered!"
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (username, password, email) VALUES (?, ?, ?)",
                   (username, generate_password_hash(password), email))
    if cursor.rowcount == 1:
        conn.commit()
        conn.close()
        send_code(get_userid(username), email)
        return "User created"
    else:
        conn.close()
        return "Couldn't create user"

def send_code(user_id, email):
    code = random.randrange(100000,999999)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO codes (user_id, code) VALUES (?, ?)",
                (user_id, code))
    if cursor.rowcount == 1:
        conn.commit()
        conn.close()
        # TODO disable for now to not spam?
        #mail.send_email(email, sitename+" Access Code","Your one-time access code to unlock your email and sign in to the dashboard is:/n/n"+str(code)+"/n/nThis code is valid for one hour.")
        return "Code sent"
    else:
        conn.close()
        return "Code not sent"

def enter_code(username, code):
    user_id = get_userid(username)
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM codes WHERE user_id=?",
                    (user_id, )).fetchall()
    conn.close()
    #for row in res:
    #    for i in row:
    #        print(i)
    ### TODO: continue here
    #print("not done yet")

enter_code("abcabc8", "123456")

def delete_user(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user WHERE username=? COLLATE NOCASE",
                        (username, ))
    if cursor.rowcount == 1:
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def list_users():
    conn=get_db_connection()
    res = conn.execute("SELECT * FROM user").fetchall()
    return res
