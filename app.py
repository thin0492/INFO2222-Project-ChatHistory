'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for, session, redirect, jsonify
from flask_socketio import SocketIO
import db
import secrets
import hashlib
import re
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from markupsafe import escape


# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

# don't remove this!!
import socket_routes

def check_session_token():
    if request.path != 'login' and request.path != '/signup' and not request.path.startswith('/static'):
        session_token = request.cookies.get('session_token')
        if not session_token or not db.get_session(session_token):
            return redirect('/login')

def authenticate_user(username):
    if 'username' in session and session['username'] == username:
        return True 
    else: 
        return False

#def is_valid_username(username):
#   return str(username).islanum()

def is_valid_password(password):
    return re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,}$', password)

def is_staff(username):
    user = db.get_user(username)
    return user and user.role.name == "Staff"

# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")

# handles a post request when the user clicks the signup button
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)

    username = escape(request.json.get("username"))
    password = escape(request.json.get("password"))

    if not is_valid_password(password):
        return "Error: Password must contain at least one number, uppercase letter, lowercase letter, special character, and be at least 8 characters long!"

    salt = secrets.token_hex(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

    if db.get_user(username) is None:
        # Assign the appropriate role to the user
        if username == "admin":
            role = db.get_role_by_name("Staff")
        else:
            role = db.get_role_by_name("Student")
        
        if role:
            db.insert_user(username, hashed_password, salt, role.id)
            return url_for('home', username=username)
        else:
            return "Error: Role not found!"
    return "Error: User already exists!"

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)

    #escape to help sanitize the user inputs before they are prcoessed or stored.
    username = escape(request.json.get("username"))
    password = escape(request.json.get("password"))

    user = db.get_user(username)
    if user is None:
        return "Error: User does not exist!"

    stored_salt = user.salt
    hashed_input_password = hashlib.pbkdf2_hmac('sha256', password.encode(), stored_salt.encode(), 100000).hex()
    
    if hashed_input_password != user.password:
        return "Error: Password does not match!"

    session['username'] = username

    return url_for('home', username=request.json.get("username"))

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

# home page, where the messaging app is
@app.route("/home")
def home():
    if request.args.get("username") is None:
        abort(404)
    username = request.args.get("username")
    friends = db.get_friends(username)
    friend_requests = db.get_friend_requests(username)
    sent_friend_requests = db.get_sent_friend_requests(username)
    chat_invitations = db.get_chat_invitations(username)
    return render_template("home.jinja", username=username, friends=friends, friend_requests=friend_requests, sent_friend_requests=sent_friend_requests, chat_invitations=chat_invitations)

@app.route("/profile")
def profile():
    username = request.args.get("username")
    if not username:
        username = request.cookies.get("username")
        if not username:
            return redirect(url_for("login"))
    user = db.get_user(username)
    if not user:
        abort(404)
    return render_template("profile.jinja", user=user)

@app.route("/knowledgerepo")
def knowledge_repo():
    username = request.cookies.get("username")
    if not username:
        return redirect(url_for("login"))

    user = db.get_user(username)
    if not user:
        abort(404)

    articles = db.get_all_articles()
    for article in articles:
        article.comments = db.get_comments_by_article(article.id)

    return render_template("knowledgerepo.jinja", user=user, articles=articles)

@app.route("/create_article", methods=["POST"])
def create_article():
    username = request.cookies.get("username")
    title = request.json.get("title")
    content = request.json.get("content")
    db.create_article(title, content, username)
    return jsonify({"success": True})

@app.route("/edit_article/<int:article_id>", methods=["POST"])
def edit_article(article_id):
    username = request.cookies.get("username")
    if not username:
        abort(403)

    user = db.get_user(username)
    article = db.get_article(article_id)

    if not user or (user.role.name != "Staff" and article.author != username):
        abort(403)

    title = request.json.get("title")
    content = request.json.get("content")
    db.update_article(article_id, title, content)
    return jsonify({"success": True})

@app.route("/delete_article/<int:article_id>", methods=["POST"])
def delete_article(article_id):
    username = request.cookies.get("username")
    if not username:
        abort(403)

    user = db.get_user(username)
    article = db.get_article(article_id)

    if not user or (user.role.name != "Staff" and article.author != username):
        abort(403)

    db.delete_article(article_id)
    return jsonify({"success": True})

@app.route("/create_comment/<int:article_id>", methods=["POST"])
def create_comment(article_id):
    username = request.cookies.get("username")
    content = request.json.get("content")
    db.create_comment(content, username, article_id)
    return jsonify({"success": True})

@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    username = request.cookies.get("username")
    if not username:
        abort(403)

    user = db.get_user(username)
    comment = db.get_comment(comment_id)

    if not user or (user.role.name != "Staff" and comment.author != username):
        abort(403)

    db.delete_comment(comment_id)
    return jsonify({"success": True})

if __name__ == '__main__':
    if not db.get_role_by_name("Student"):
        db.create_role("Student")
    if not db.get_role_by_name("Staff"):
        db.create_role("Staff")
    socketio.run(app)#, ssl_context=('cert/info.test.crt','cert/info.test.key'))