from flask import render_template, send_file, request, Blueprint, make_response, current_app, redirect, Response, jsonify

from functools import wraps

import api.user as user
import dashboard.context as context

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
    try:
        context_data = context.get_context(request.args)
        return { "context": context_data }
    except Exception as e:
        return { "error": str(e) }, 500

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
    return render_template('settings.html', user = user.get_user_dict())
