from flask import render_template, send_file, request, Blueprint, make_response, current_app, redirect, Response
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
    return browser()
    #return health_check()
    #return redirect("health-check.html?hidden=;3;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;21;23;24;25;27;26;28;30;31;32;33;35;29;37;")
    #return redirect("health-check.html?hidden=;3;5;7;8;11;12;14;15;16;18;19;21;23;24;25;28;30;31;32;33;29;;4;38;;36;;43;44;42;41;40;;27;;34;35;;;9;;;;;10;")

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
                if level == 1 or int(user.get_user_level(cookies["Email"], cookies["SessionID"])) >= level:
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

@dashboard_bp.route("/get_user_level", methods=['POST'])
def getUserLevel():
    sessionID = request.args.get('SessionID')
    email = request.args.get('email')
    if email == None or email == "" or sessionID == None or sessionID == "":
        return "Couldn't get user level or session"
    return make_response(user.get_user_level(email, sessionID))

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
    
    # TODO: This used to return False or users but now returns true or false, frontend should request the data again - not us
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

@dashboard_bp.route("/getcontext", methods=['GET'])
def getContext():
    return { "context": context.get_context(request.args) }

###########################################################
###                 main web templates                  ###
###########################################################

@dashboard_bp.route("/noacess.html")
def noaccess():
    return render_template('noaccess.html')

@dashboard_bp.route("/map.html")
def map():
    # data needed: health_score_summary, usage_summary, metadata (floor area, descriptions, categories)
    return render_template('map.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/benchmark.html")
def benchmark():
    # data needed: health_score_summary, usage_summary, metadata (floor area, descriptions, categories)
    return render_template('benchmark.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/browser.html")
def browser():
    # data needed: health_score_summary, [usage_summary - not sure, maybe for a starting page overview?], metadata (floor area, descriptions, categories)
    return render_template('browser.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/health-check.html")
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def health_check():
    # data needed: [health_score_summary, usage_summary - not sure, maybe for a starting page overview?], metadata (floor area, descriptions, categories)
    hc_latest = api_bp.meter_health().json
    if len(hc_latest) > 0: # type: ignore
        return render_template('health-check.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json, hc_latest = hc_latest, hc_meta = api_bp.hc_meta().json, context = context.view_all())
    else:
        return render_template('health-check.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json, hc_latest = api_bp.devices().json, hc_meta = api_bp.hc_meta().json, context = context.view_all())

@dashboard_bp.route("/anomaly.html")
#@required_user_level(3)
def anomaly():
    return render_template('anomaly.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/energy-usage.html")
#@required_user_level(3)
def energyusage():
    return render_template('energy-usage.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/context.html")
@required_user_level("USER_LEVEL_VIEW_COMMENTS")
def context_view():
    data = context.view_all()
    return render_template('context.html', data = data, devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

@dashboard_bp.route("/about.html")
def about():
    return render_template('about.html')

@dashboard_bp.route("/settings.html")
def settings():
    return render_template('settings.html', user = user.get_user())

###########################################################
###            others (not in main layout)              ###
###########################################################

#@dashboard_bp.route("/start.html")
#@required_user_level(1)
#def start():
#    return render_template('start.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)

#@dashboard_bp.route("/tutorial.html")
#def tutorial():
#    return render_template('tutorial.html')

#@dashboard_bp.route("/devices.html")
#@required_user_level(3)
#def devices():
#    return render_template('devices.html', devices = api_bp.devices().json, masterlist = api_bp.usageoffline().json)
