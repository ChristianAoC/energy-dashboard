from flask import render_template, send_file, request, Blueprint, make_response, current_app, redirect, Response, jsonify
from markupsafe import escape
import api.api as api_bp
import dashboard.user as user
import dashboard.context as context
from functools import wraps

dashboard_bp = Blueprint('dashboard_bp'
    , __name__,
    static_url_path='/static',
    template_folder='templates',
    static_folder='static')

###########################################################
###            start page and general stuff             ###
###########################################################

@dashboard_bp.route("/helloworld")
def helloworld():
    return current_app.config["SITE_NAME"]

@dashboard_bp.route("/")
def index():
    return redirect("/browser")

@dashboard_bp.route("/favicon.ico")
def getFavicon():
    return send_file('static/gfx/favicon.ico')

###########################################################
###                  user management                    ###
###########################################################

# decorator to limit certain pages to a specific user level
def required_user_level(level_config_key):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            cookies = request.cookies
            try:
                level = int(current_app.config[level_config_key])
                email = cookies.get("Email", None)
                sessionID = cookies.get("SessionID", None)

                if user.get_user_level(email, sessionID) >= level:
                    return function(*args, **kwargs)
            except:
                print("No or wrong cookie")
            return noaccess()
        return wrapper
    return decorator

def setCookies(email: str, sessionID: str) -> Response:
    resp = make_response(render_template('settings.html', user = user.get_user(email)))
    resp.set_cookie("SessionID", sessionID, 60*60*24*365)
    resp.set_cookie("Email", email, 60*60*24*365)
    resp.status_code = 200
    return resp

@dashboard_bp.route("/logout", methods=['POST'])
def logout():
    email = request.args.get('email')
    if email == None or email == "":
        return "No email provided."
    resp = make_response(render_template('settings.html'))
    resp.delete_cookie('SessionID')
    resp.delete_cookie('Email')
    return resp

@dashboard_bp.route("/loginrequest", methods=['POST'])
def loginRequest():
    email = request.args.get('email')
    if email == None or email == "":
        return make_response("No email provided.", 400)
    
    result = user.login_request(email)
    
    if result[1] != 200:
        return make_response(result[0], result[1])

    if result[0] is str:
        return make_response(result[0], result[1])
    
    return setCookies(result[0][1], result[0][2])

@dashboard_bp.route("/verify_login")
def verifyLogin():
    email = request.args.get('email')
    if email is None or email == "":
        return make_response("No email provided.", 400)
    code = request.args.get('code')
    if code is None or code == "":
        return make_response("No code provided.", 400)

    result = user.check_code(email, code)
    if result[0] == False:
        return make_response(result[1], 500)
    
    return setCookies(email, result[1])

@dashboard_bp.route("/get_user_level", methods=['GET', 'POST'])
def getUserLevel():
    sessionID = request.args.get('SessionID')
    email = request.args.get('email')
    if email == None or email == "" or sessionID == None or sessionID == "":
        return make_response("Couldn't get user level or session", 400)
    return make_response(str(user.get_user_level(email, sessionID)), 200)

@dashboard_bp.route("/admin/set_user_level", methods=['POST'])
@required_user_level("USER_LEVEL_ADMIN")
def setUserLevel():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    email = data.get('email')
    level = data.get('level')    
    if email == None or level == None:
        return make_response("No email or level specified", 400)
    
    userChange = user.get_user(email)
    
    if userChange is None:
        return make_response("Couldn't load user", 500)
    
    userChange["level"] = level
    
    success = user.update_user(userChange)
    if not success:
        return make_response("Failed to update user", 500)
    
    return make_response("Successfully updated user", 200)

@dashboard_bp.route('/admin/delete_user', methods=['POST'])
@required_user_level("USER_LEVEL_ADMIN")
def deleteUser():
    data = request.get_json()
    if not data:
        return make_response("No JSON data received", 400)
    
    email = data.get('email')
    if email == None:
        return make_response("No email specified", 400)
    
    result = user.delete_user(email)
    if not result:
        return make_response(f"Couldn't remove user {email}", 500)
    
    return make_response(f"Successfully removed user {email}", 200)

@dashboard_bp.route('/admin/list_users')
@required_user_level("USER_LEVEL_ADMIN")
def listUsers():
    return user.list_users()

###########################################################
###               context functionality                 ###
###########################################################

@dashboard_bp.route("/addcontext", methods=['POST'])
def addContext():
    contextElem = request.json
    return context.add_context(contextElem)

@dashboard_bp.route("/editcontext", methods=['POST'])
def editContext():
    contextElem = request.json
    return context.edit_context(contextElem)

@dashboard_bp.route("/deletecontext", methods=['POST'])
def deleteContext():
    contextID = request.args.get('contextID')
    return context.delete_context(contextID)

@dashboard_bp.route("/allcontext", methods=['GET'])
def allContext():
    return jsonify(context.view_all())

###########################################################
###                 main web templates                  ###
###########################################################

@dashboard_bp.route("/noacess")
def noaccess():
    return render_template('noaccess.html')

@dashboard_bp.route("/map")
def map():
    return render_template('map.html')

@dashboard_bp.route("/benchmark")
def benchmark():
    return render_template('benchmark.html')

@dashboard_bp.route("/browser")
def browser():
    return render_template('browser.html')

@dashboard_bp.route("/health-check")
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def health_check():
    return render_template('health-check.html')

@dashboard_bp.route("/context")
@required_user_level("USER_LEVEL_VIEW_COMMENTS")
def context_view():
    return render_template('context.html')

@dashboard_bp.route("/about")
def about():
    return render_template('about.html')

@dashboard_bp.route("/settings")
def settings():
    return render_template('settings.html', user = user.get_user())
