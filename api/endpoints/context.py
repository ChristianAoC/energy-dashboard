from flask import Blueprint, make_response, request, render_template, redirect, url_for, jsonify, current_app

import api.users as users
import api.context as context
import dashboard.main as dashboard_bp

context_api_bp = Blueprint('context_api_bp',
                         __name__,
                         static_url_path='/static',
                         template_folder='/dashboard/templates',
                         static_folder='static')

###########################################################
###               context functionality                 ###
###########################################################

@context_api_bp.route("/add", methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
def addContext():
    contextElem = request.json
    if contextElem is None:
        return make_response("Invalid context", 400)
    
    # for global mute run user level check just to be sure
    if contextElem["type"] == "Global-mute":
        cookies = request.cookies
        email = cookies.get("Email", None)
        sessionID = cookies.get("SessionID", None)
        if users.get_user_level(email, sessionID) < current_app.config["USER_LEVEL_EDIT_COMMENTS"]:
            return make_response("Unauthorised", 401)
    
    return context.add_context(contextElem)

@context_api_bp.route("/edit", methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
def editContext():
    contextElem = request.json
    if not contextElem:
        return make_response("Missing context element", 400)
    if contextElem["type"] == "Global-mute":
        cookies = request.cookies
        email = cookies.get("Email", None)
        sessionID = cookies.get("SessionID", None)
        if users.get_user_level(email, sessionID) < 4:
            return make_response("Unauthorised", 401)
    return context.edit_context(contextElem)

@context_api_bp.route("/delete", methods=['POST'])
@dashboard_bp.required_user_level("USER_LEVEL_SUBMIT_COMMENTS")
def deleteContext():
    contextID = request.args.get('contextID')
    if not contextID:
        return make_response("Missing contextID", 400)
    cookies = request.cookies
    email = cookies.get("Email", None)
    sessionID = cookies.get("SessionID", None)
    if email is None or sessionID is None:
        return make_response("Unauthorised", 401)
    user_level = users.get_user_level(email, sessionID)
    if user_level < 4:
        return make_response("Unauthorised", 401)
    return context.delete_context(contextID)

@context_api_bp.route("/all", methods=['GET'])
@dashboard_bp.required_user_level("USER_LEVEL_VIEW_COMMENTS")
def getContext():
    return jsonify(context.view_all())