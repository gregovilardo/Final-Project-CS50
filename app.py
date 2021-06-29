import os
import sys
from os import listdir
from os.path import isfile, isdir, join
import time
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory, g
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.utils import secure_filename
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from sqlite3 import Error
from pathlib import Path
from helpers import login_required

# from datetime import datetime
# import re

#where videos upload goes and allowing only mp4
UPLOAD_FOLDER_VID = "X:\\Portfolio\\slackproject\\static\\videos"
UPLOAD_FOLDER_IMG = "X:\\Portfolio\\slackproject\\static\\profilePics"
ALLOWED_EXTENSIONS_VID = set(["mp4"])
ALLOWED_EXTENSIONS_IMG = set(["jpeg", "png", "bmp", "jpg"])
DATABASE = "X:\\Portfolio\\slackproject\\db\\DBslack.db"

class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        variable_start_string='[[',  # Default is '{{', I'm changing this because Vue.js uses '{{' / '}}'
        variable_end_string=']]',
    ))

app = CustomFlask(__name__)
# app = Flask(__name__)

app.secret_key = "super secret key"
app.config["UPLOAD_FOLDER_VID"] = UPLOAD_FOLDER_VID
app.config["UPLOAD_FOLDER_IMG"] = UPLOAD_FOLDER_IMG

# look properly what this mean
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#open the db
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

#close the db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_VID

def allowed_pic(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMG

@app.route("/")
@login_required
def index():

    with app.app_context():
        db = get_db()
        c = db.cursor()
        c.execute("SELECT name, route, user, pic FROM videos INNER JOIN users ON users.username = videos.user")
        feeds = [dict(row) for row in c]
        #changue the route becouse flask accept it like that
        for r in feeds:
            r["pic"] = r["pic"].replace("X:\Portfolio\slackproject\static\\profilePics\\", "../static/profilePics/")
            r["route"] = r["route"].replace("X:\Portfolio\slackproject\static\\videos\\", "../static/videos/")

    error = request.args.get("error")
    return render_template("index.html", feeds=feeds, error=error)


@app.route("/uploadVideo", methods=["POST"])
@login_required
def uploadVideo():
    

    with app.app_context():
        db = get_db()
        c = db.cursor()
        username = c.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]
        if not request.form.get("videoName"):
            print("no video name")
            return redirect("index")
        else:
            video_name = request.form.get('videoName')
        if 'file' not in request.files:
            print("No file has been upload")
        else:
            file = request.files['file']
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                print('No selected file')
            if file and allowed_file(file.filename):
                filename = secure_filename(video_name) + '.mp4'
                file.save(os.path.join(app.config['UPLOAD_FOLDER_VID'], filename))
                route = UPLOAD_FOLDER_VID + "\\" + filename               
                print(route)
                print(filename)
                try:
                    c.execute("INSERT INTO videos (name, route, user) VALUES (?, ?, ?)", (video_name, route, username))
                    db.commit()
                    print("successssssss")
                except:
                    print("error inserting video data")
                return render_template("index.html", uploaded_video="../static/videos/" + filename)
            else:
                return redirect(url_for(".index", error="You must upload a .mp4 file"))


@app.route("/searchVideo", methods=["POST"])
@login_required
def searchVideo():

    with app.app_context():
        db = get_db()
        c = db.cursor()
        if request.form.get("videoNameTrick"):
            print(request.form.get("videoNameTrick"))
            c.execute("SELECT name, route FROM videos WHERE name LIKE ?", (request.form.get("videoNameTrick"),))
            search_videos = [dict(row) for row in c]
            #flask accept this route
            for r in search_videos:
                r["route"] = r["route"].replace("X:\Portfolio\slackproject\static\\videos\\", "../static/videos/")
            print(search_videos)
            return render_template("videos.html", search_videos=search_videos)
        else:
            print("quepasa")
@app.route("/deleteVideo", methods=["POST"])
@login_required
def deleteVideo():

    with app.app_context():
        db = get_db()
        c = db.cursor()
        if request.form.get("videoToDelete"):
            try:
                c.execute("DELETE FROM videos WHERE id = ?", (request.form.get("videoToDelete"),))
                db.commit()
                print("successssssss")
            except:
                print("error deleting video")
            return redirect("profile")


@app.route("/uploadProfPic", methods=["POST"])
@login_required
def uploadProfPic():

    with app.app_context():
        db = get_db()
        c = db.cursor()
        username = c.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]
        if 'file' not in request.files:
            print("No file has been upload")
            return redirect("profile")
        else:
            file = request.files['file']
            if file.filename == '':
                print('No selected file')
            if file and allowed_pic(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_IMG'], filename))
                route = UPLOAD_FOLDER_IMG + "\\" + filename             
                print(route)
                print(filename)
                try:
                    c.execute("UPDATE users SET pic = ? WHERE username = ?", (route, username))
                    db.commit()
                    print("successssssss")
                except:
                    print("error inserting profile picture")
                return redirect("profile")
            else:
                print("este error")
                return redirect("profile")

@app.route("/deleteProfilePic", methods=["POST"])
@login_required
def deleteProfilePic():

    with app.app_context():
        db = get_db()
        c = db.cursor()
        username = c.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]
        route = ""
        try:
            c.execute("UPDATE users SET pic = ? WHERE username = ?", (route, username))
            db.commit()
            print("successssssss")
        except:
            print("error deleting prof pict")
        return redirect("profile")


@app.route("/login", methods=["GET", "POST"])
def login():

    #forget any user_id
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            print('error username')
        if not request.form.get("password"):
            print("error pw")
            
        with app.app_context():
            db = get_db()
            c = db.cursor()
            #query db for username
            username = request.form.get("username")
            print(username)
            rows = c.execute("SELECT * FROM users WHERE username = (?)", (request.form.get("username"),)).fetchall()

            # check if pw or username is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                print("invalid username and/or password")
                error = "Invalid password or email"
                with app.app_context():
                    db = get_db()
                    c = db.cursor()
                    allUsers = [allUser[0] for allUser in c.execute("SELECT username FROM users")]
                    usersLen = len(allUsers)
                return render_template("login.html", error=error, allUsers=allUsers, usersLen=usersLen)
            
            #remember which user has logged in
            session["user_id"] = rows[0]["id"]

            return redirect("/")
    
    else:
        with app.app_context():
            db = get_db()
            c = db.cursor()
            allUsers = [allUser[0] for allUser in c.execute("SELECT username FROM users")]
            usersLen = len(allUsers)
        return render_template('login.html', allUsers=allUsers, usersLen=usersLen)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "GET":
        with app.app_context():
            db = get_db()
            c = db.cursor()
            username = c.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]

            if (c.execute("SELECT pic FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0] != None):
                profilePic = c.execute("SELECT pic FROM users WHERE id = ?", (session["user_id"],)).fetchone()[0]
                profilePic = profilePic.replace("X:\Portfolio\slackproject\static\\profilePics\\", "../static/profilePics/")
                print(profilePic)
                c.execute("SELECT id, route, name FROM videos WHERE user = (?)", (username,))
                uservideos = [dict(row) for row in c]
                #flask accept this route
                for r in uservideos:
                    r["route"] = r["route"].replace("X:\Portfolio\slackproject\static\\videos\\", "../static/videos/")
                return render_template("profile.html", profilePic=profilePic, uservideos=uservideos, username=username)
            else:
                return render_template("profile.html", username=username)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()
    if request.method == "POST":

        with app.app_context():
            db = get_db()
            c = db.cursor()
            # Ensure username was submitted
            if not request.form.get("user"):
                print("You must provide an username")
            
            isUser = c.execute("SELECT username FROM users WHERE username = (?)", (request.form.get("user"),)).fetchone()

            if isUser == None:
                username = request.form.get("user")
            else:
                print(isUser[0])
                print("Username already exist")
        
            if not request.form.get("password"):
                print("You must provide a password")
            elif request.form.get("confirmation") != request.form.get("password"):
                print("Passwords does not match")
            else:
                password_hash = generate_password_hash(request.form.get("password"))


            try:
                if username and password_hash:
                    try:
                        c.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, password_hash))
                        db.commit()
                        print('data inserted')
                    except:
                        print('error inserting data')
            except UnboundLocalError:
                print("Error")

            # Redirect user to home page
            return redirect("/")

    else:
        return redirect("/login")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
    app.debug = True
    app.run()






