from flask import Blueprint, make_response, request, render_template, redirect, url_for

import api.users as users
import dashboard.main as dashboard_bp

users_api_bp = Blueprint('users_api_bp',
                         __name__,
                         static_url_path='/static',
                         template_folder='/dashboard/templates',
                         static_folder='static')

@users_api_bp.route("/logout/", methods=['POST'])
@users_api_bp.route("/logout", methods=['POST'])
def logout():
    email = request.args.get('email')
    if email is None or email == "":
        return "No email provided."
    
    session_id = request.cookies.get('SessionID')
    if session_id is not None:
        users.delete_session(email, session_id)
    
    resp = make_response(render_template('settings.html'))
    resp.delete_cookie('SessionID')
    resp.delete_cookie('Email')
    return resp

@users_api_bp.route("/login/", methods=['POST'])
@users_api_bp.route("/login", methods=['POST'])
def login():
    email = request.args.get('email')
    if email is None or email == "":
        return make_response("No email provided.", 400)
    
    result = users.login_request(email)
    
    if result[1] != 200:
        return make_response(result[0], result[1])

    if isinstance(result[0], str):
        return make_response(result[0], result[1])
    
    return users.set_cookies(result[0][0], result[0][1])

@users_api_bp.route("/verify/")
@users_api_bp.route("/verify")
def verify():
    email = request.args.get('email')
    code = request.args.get('code')

    if not email or not code:
        return make_response("Email or code not provided.", 400)

    logged_in_user = users.get_logged_in_user()
    if logged_in_user and logged_in_user['email'].lower() == email.lower():
        # redirect with message
        return redirect(url_for('dashboard_bp.settings', message=f"Already logged in as {email}.", status="info"))

    success, result = users.check_code(email, code)
    if not success:
        return redirect(url_for('dashboard_bp.settings', message=result, status="error"))

    # success — set cookies and redirect with success message
    resp = make_response(redirect(url_for('dashboard_bp.settings', message="Login successful!", status="success")))
    resp.set_cookie("SessionID", result, max_age=60*60*24*365)
    resp.set_cookie("Email", email, max_age=60*60*24*365)
    return resp

@users_api_bp.route("/get-level/")
@users_api_bp.route("/get-level")
def get_level():
    session_id = request.args.get('SessionID')
    email = request.args.get('email')
    if email is None or email == "" or session_id is None or session_id == "":
        return make_response("Couldn't get user level or session", 400)
    return make_response(str(users.get_user_level(email, session_id)), 200)

@users_api_bp.route("/set-level/", methods=['POST'])
@users_api_bp.route("/set-level", methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def set_level():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    
    email = data.get('email')
    if email is None:
        return make_response("No email specified", 400)
    
    level = data.get('level')
    if level is None:
        return make_response("No level specified", 400)
    
    success = users.set_level(email, level)
    if not success:
        return make_response("Failed to update user", 500)
    
    return make_response("Successfully updated user", 200)

@users_api_bp.route('/delete/', methods=['POST'])
@users_api_bp.route('/delete', methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def delete():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    
    email = data.get('email')
    if email is None:
        return make_response("No email specified", 400)
    
    result = users.delete_user(email)
    if not result:
        return make_response(f"Couldn't remove user {email}", 500)
    
    return make_response(f"Successfully removed user {email}", 200)

@users_api_bp.route('/list/')
@users_api_bp.route('/list')
@dashboard_bp.required_user_level("USER_LEVEL_ADMIN")
def user_list():
    return users.list_users()