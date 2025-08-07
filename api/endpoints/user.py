from flask import Blueprint, make_response, request, render_template

import api.users as users
import dashboard.main as dashboard_bp

users_api_bp = Blueprint('users_api_bp',
                         __name__,
                         static_url_path='/static',
                         template_folder='/dashboard/templates',
                         static_folder='static')

@users_api_bp.route("/logout", methods=['POST'])
def logout():
    email = request.args.get('email')
    if email == None or email == "":
        return "No email provided."
    
    session_id = request.cookies.get('SessionID')
    if session_id is not None:
        users.delete_session(email, session_id)
    
    resp = make_response(render_template('settings.html'))
    resp.delete_cookie('SessionID')
    resp.delete_cookie('Email')
    return resp

@users_api_bp.route("/login", methods=['POST'])
def login():
    email = request.args.get('email')
    if email is None or email == "":
        return make_response("No email provided.", 400)
    
    result = users.login_request(email)
    
    if result[1] != 200:
        return make_response(result[0], result[1])

    if result[0] is str:
        return make_response(result[0], result[1])
    
    return users.set_cookies(result[0][0], result[0][1])

@users_api_bp.route("/verify")
def verify():
    email = request.args.get('email')
    if email is None or email == "":
        return make_response("No email provided.", 400)
    code = request.args.get('code')
    if code is None or code == "":
        return make_response("No code provided.", 400)

    result = users.check_code(email, code)
    if result[0] == False:
        return make_response(result[1], 500)
    
    return users.set_cookies(email, result[1])

@users_api_bp.route("/get-level", methods=['GET', 'POST'])
def get_level():
    sessionID = request.args.get('SessionID')
    email = request.args.get('email')
    if email == None or email == "" or sessionID == None or sessionID == "":
        return make_response("Couldn't get user level or session", 400)
    return make_response(str(users.get_user_level(email, sessionID)), 200)

@users_api_bp.route("/set-level", methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def set_level():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    
    email = data.get('email')
    if email == None:
        return make_response("No email specified", 400)
    
    level = data.get('level')
    if level == None:
        return make_response("No level specified", 400)
    
    success = users.set_level(email, level)
    if not success:
        return make_response("Failed to update user", 500)
    
    return make_response("Successfully updated user", 200)

@users_api_bp.route('/delete', methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def delete():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    
    email = data.get('email')
    if email == None:
        return make_response("No email specified", 400)
    
    result = users.delete_user(email)
    if not result:
        return make_response(f"Couldn't remove user {email}", 500)
    
    return make_response(f"Successfully removed user {email}", 200)

@users_api_bp.route('/list')
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def list():
    return users.list_users()