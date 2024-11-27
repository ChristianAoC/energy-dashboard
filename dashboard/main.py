from flask import render_template, send_file, request, Blueprint, make_response
from markupsafe import escape
import api.api as api_bp
import dashboard.db as db
#import dashboard.cache as cache
import dashboard.context as context

dashboard_bp = Blueprint('dashboard_bp'
    , __name__,
    static_url_path='',
    template_folder='templates',
    static_folder='static')

###########################################################
###            start page and general stuff             ###
###########################################################

@dashboard_bp.route("/")
def index():
    return start()

@dashboard_bp.route("/favicon.ico")
def getFavicon():
    return send_file('dashboard/static/gfx/favicon.ico')

###########################################################
###                  user management                    ###
###########################################################

@dashboard_bp.route("/loginrequest", methods=['POST'])
def loginRequest():
    username = request.args.get('username')
    password = request.args.get('password')
    res = "loginfailed"
    if db.check_login(username, password):
        res = "loginok"
        # change to this below once we movie cookie logic to flask
        #res = make_response("loginok")
        #res.set_cookie('username', username)
    return res

@dashboard_bp.route("/registerrequest", methods=['POST'])
def registerRequest():
    username = request.args.get('username')
    password = request.args.get('password')
    email = request.args.get('email')
    return db.add_user(username, password, email)

@dashboard_bp.route("/changepassword", methods=['POST'])
def changePassword():
    username = request.args.get('username')
    password = request.args.get('password')
    newPW = request.args.get('newPW')
    return db.change_password(username, password, newPW)

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
    return { "context": escape(context.get_context(request.args)) }

###########################################################
###                 main web templates                  ###
###########################################################

@dashboard_bp.route("/tutorial.html")
def tutorial():
    return render_template('tutorial.html')

@dashboard_bp.route("/start.html")
def start():
    return render_template('start.html', devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/devices.html")
def devices():
    return render_template('devices.html', devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/anomaly.html")
def anomaly():
    return render_template('anomaly.html', devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/energy-usage.html")
def energyusage():
    return render_template('energy-usage.html', devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/context.html")
def context_view():
    data = context.view_all()
    return render_template('context.html', data = data, devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/statistics.html")
def statistics():
    return render_template('statistics.html', devices = api_bp.devices(), masterlist = api_bp.usageoffline())

@dashboard_bp.route("/settings.html")
def settings():
    return render_template('settings.html')

@dashboard_bp.route("/about.html")
def about():
    return render_template('about.html')

###########################################################
###            others (not in main layout)              ###
###########################################################

@dashboard_bp.route("/apitest.html")
def apitest():
    return render_template('apitest.html')

###########################################################
###              getting and caching data               ###
###########################################################

# CURRENTLY NOT IN USE
#@dashboard_bp.route("/getdata/<endpoint>", methods=['GET', 'POST'])
#def getData(endpoint):
#    if endpoint != "summary":
#        return "Only summary endpoint supported."
#    
#    return cache.getData(endpoint, request.args)

