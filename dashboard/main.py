from flask import render_template, send_file, request, Blueprint, make_response, redirect, g

from functools import wraps

import api.users as users
import log

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
    return g.settings["site"]["SITE_NAME"]

@dashboard_bp.route("/")
def index():
    return redirect("/" + g.settings["site"]["default_start_page"])

@dashboard_bp.route("/favicon.ico")
def get_favicon():
    return send_file('static/gfx/favicon.ico')

###########################################################
###                  user management                    ###
###########################################################

# decorator to limit certain pages to a specific user level
def required_user_level(level_config_key):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                required_level = g.settings["users"][level_config_key]
                
                # Skip validating if required level is 0 (allow unauthenticated users)
                if required_level != 0:
                    cookies = request.cookies
                    email = cookies.get("Email", None)
                    session_id = cookies.get("SessionID", None)

                    if users.get_user_level(email, session_id) < required_level:
                        if request.method == "POST":
                            return make_response("Access Denied", 401)
                        return no_access()
            except Exception as e:
                print("No or wrong cookie")
                log.write(msg="No or wrong cookie", extra_info=str(e), level=log.warning)
                if request.method == "POST":
                    return make_response("Access Denied", 401)
                return no_access()
            
            return function(*args, **kwargs)
        return wrapper
    return decorator

###########################################################
###                 main web templates                  ###
###########################################################

@dashboard_bp.route("/no-access")
def no_access():
    return render_template('noaccess.html')

@dashboard_bp.route("/map")
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def campus_map():
    return render_template('map.html')

@dashboard_bp.route("/benchmark")
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def benchmark():
    return render_template('benchmark.html')

@dashboard_bp.route("/browser")
@required_user_level("USER_LEVEL_VIEW_DASHBOARD")
def browser():
    return render_template('browser.html')

@dashboard_bp.route("/health-check")
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def health_check():
    return render_template('health-check.html')

@dashboard_bp.route("/capavis")
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def capavis():
    return render_template('capavis.html')

@dashboard_bp.route("/clustering")
@required_user_level("USER_LEVEL_VIEW_HEALTHCHECK")
def clustering():
    return render_template('clustering.html')

@dashboard_bp.route("/context")
@required_user_level("USER_LEVEL_VIEW_COMMENTS")
def context_view():
    return render_template('context.html')

@dashboard_bp.route("/about")
def about():
    return render_template('about.html')

@dashboard_bp.route("/settings")
def settings():
    user = users.get_logged_in_user()
    message = request.args.get('message')
    status = request.args.get('status', 'info')  # default to "info" if not provided
    return render_template('settings.html', user=user, message=message, status=status)
