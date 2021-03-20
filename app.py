######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

# FLASK_APP=app.py FLASK_DEBUG=1 python -m flask run

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64, time, operator

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()


def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	supress = True
	if request.args.get('supress')=='False':
		supress = False
	return render_template('register.html', supress=supress)

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		firstname=request.form.get('firstname')
		lastname=request.form.get('lastname')
		date_of_birth=request.form.get('date_of_birth')
	except Exception as e:
		print(e)
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		if date_of_birth:
			print(cursor.execute(
				"INSERT INTO Users (email, password, firstname, lastname, date_of_birth) \
				 VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')".format(email, password, firstname, lastname, date_of_birth)))
		else:
			print(cursor.execute(
				"INSERT INTO Users (email, password, firstname, lastname) \
				 VALUES ('{0}', '{1}', '{2}', '{3}')".format(email, password, firstname, lastname)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("email is already used")
		return flask.redirect(flask.url_for('register', supress=False))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile", user=uid)



@app.route('/friends', methods=['GET'])
@flask_login.login_required
def Friends():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	User_Friends_list = findUserFriends(uid)
	recommendedFriends = getRecomendedFriends(uid)
	return render_template('friends.html', name=flask_login.current_user.id, message='Your friends list', friends=User_Friends_list, recommendedFriends=recommendedFriends)

@app.route('/searchFriends')
@flask_login.login_required
def search():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	recommendedFriends = getRecomendedFriends(uid)
	return render_template('searchFriends.html', recommendedFriends=recommendedFriends)

@app.route('/searchFriends', methods=['POST'])
@flask_login.login_required
def searchFriends():
	try:
		name=request.form.get('name')
	except:
		print ("couldn't find all tokens")
		return flask.redirect(flask.url_for('friends'))
	cursor = conn.cursor()
	cursor.execute("SELECT email, firstname, lastname FROM Users WHERE firstname = '{0}' OR lastname = '{0}'".format(name))
	Friends_list = cursor.fetchall()
	uid=getUserIdFromEmail(flask_login.current_user.id)
	User_Friends_list = findUserFriends(uid)
	Friends_list = [x for x in Friends_list if x[1:] not in User_Friends_list]
	return render_template('searchFriends.html', name=flask_login.current_user.id, message='Here\'s Your Search Result.', searchResult=Friends_list)

@app.route('/addFriends', methods=['GET'])
@flask_login.login_required
def addFriends():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	f_email=request.args.get('values')
	f_firstname=getUserFirstName(f_email)
	f_lastname=getUserLastName(f_email)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Friends (f_email, user_id, f_firstname, f_lastname) VALUES ('{0}', '{1}', '{2}', '{3}')".format(f_email, uid, f_firstname, f_lastname))
	conn.commit()
	User_Friends_list = findUserFriends(uid)
	return render_template('friends.html', name=flask_login.current_user.id, message='You add a friend!', friends=User_Friends_list)


def findUserFriends(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT f_firstname, f_lastname FROM Friends WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

def getUserFirstName(email):
	cursor = conn.cursor()
	cursor.execute("SELECT firstname From Users Where email = '{0}'".format(email))
	return cursor.fetchone()[0]

def getUserLastName(email):
	cursor = conn.cursor()
	cursor.execute("SELECT lastname From Users Where email = '{0}'".format(email))
	return cursor.fetchone()[0]

def getRecomendedFriends(uid):
	recommendedFriends = [[],[]]
	cursor = conn.cursor()
	cursor.execute("SELECT f_email, f_firstname, f_lastname FROM Friends WHERE user_id = '{0}'".format(uid))
	friend_emails = cursor.fetchall()
	for friend_email in friend_emails:
		cursor = conn.cursor()
		sql = "SELECT user_id FROM Users WHERE email = %s"
		cursor.execute(sql, friend_email[0])
		friend_id = cursor.fetchone()[0]
		cursor = conn.cursor()
		cursor.execute(("SELECT f_firstname, f_lastname FROM Friends WHERE user_id = %s AND f_email != %s"), (friend_id, flask_login.current_user.id))
		fs_of_f = cursor.fetchall()
		for f_of_f in fs_of_f:
			if f_of_f in recommendedFriends[1]:
				recommendedFriends[0][recommendedFriends[1].index(f_of_f)] += 1
			else:
				recommendedFriends[0].append(0)
				recommendedFriends[1].append(f_of_f)
	sorted_r_friends = []
	for i in range(len(recommendedFriends[0])):
		sorted_r_friends.append([recommendedFriends[0][i], recommendedFriends[1][i]])
	sorted_r_friends = sorted(sorted_r_friends, reverse=True)
	return sorted_r_friends

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		tags = request.form.get('tags')
		tags = [x.strip('#') for x in tags.split(' ')]
		photo_data = base64.b64encode(imgfile.read())
		try:
			AlbumName=request.form.get('album')
		except:
			print ("couldn't find all tokens at line 186")
			return flask.redirect(flask.url_for('upload'))
		albums_id = findAlbumIdFromName(AlbumName)
		albumn_user_id = findAlbumUserID(albums_id)
		if albumn_user_id == uid:
			cursor = conn.cursor()
			cursor.execute('''INSERT INTO Pictures (photos_path, caption, photos_owner_id, Albums_albums_id) VALUES (%s, %s, %s, %s )''' ,(photo_data, caption, uid, albums_id))
			conn.commit()
			photos_id = findPhotoId(photo_data, caption, albums_id)
			cursor = conn.cursor()
			for i in range(len(tags)):
				if isTagUnique(tags[i]):
					if isTagAlreadyExist(tags[i]):
						cursor.execute("INSERT INTO Photos_has_Tags (Photos_photos_id, Tags_tags_text) VALUES ('{0}', '{1}')".format(photos_id, tags[i]))
					else:
						cursor.execute("INSERT INTO Tags (tags_text) VALUES ('{0}')".format(tags[i]))
						cursor.execute("INSERT INTO Photos_has_Tags (Photos_photos_id, Tags_tags_text) VALUES ('{0}', '{1}')".format(photos_id, tags[i]))
				else:
					cursor.execute("INSERT INTO Photos_has_Tags (Photos_photos_id, Tags_tags_text) VALUES ('{0}', '{1}')".format(photos_id, tags[i]))
			conn.commit()
			return render_template('profile.html', name=flask_login.current_user.id, message='Photo uploaded!')
		else:
			return render_template('profile.html', name=flask_login.current_user.id, message='Wrong user!')
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		albums_list = findUserAlbums(uid)
		return render_template('upload.html', albums=albums_list)

@app.route('/createAlbums')
@flask_login.login_required
def Albums():
	return render_template('createAlbums.html')

@app.route('/createAlbums', methods=['POST'])
@flask_login.login_required
def createAlbums():
	try:
		albums_name=request.form.get('AlbumName')
	except:
		print ("couldn't find all tokens at line 186")
		return flask.redirect(flask.url_for('createAlbums'))
	date_of_creation = time.strftime("%Y-%m-%d")
	albums_owner_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Albums (albums_name, Users_user_id, date_of_creation) VALUES ('{0}', '{1}', '{2}')".format(albums_name, albums_owner_id, date_of_creation))
	conn.commit()
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, albums_name, date_of_creation FROM Albums WHERE Users_user_id = '{0}'".format(uid))
	Albums_list= cursor.fetchall()
	return render_template('albums.html', name=flask_login.current_user.id, message='Album Created!', albums=Albums_list)

@app.route('/albums', methods=['GET'])
@flask_login.login_required
def findAlbums():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, albums_name, date_of_creation FROM Albums WHERE Users_user_id = '{0}'".format(uid))
	Albums_list= cursor.fetchall()
	return render_template('albums.html', name=flask_login.current_user.id, message='Here\'s your albums', albums=Albums_list)

@app.route('/photos/<albums_id>', methods=['GET'])
def gotothisalbum(albums_id):
	photos_list=findPhotosInAlbums(albums_id)
	AlbumName=findAlbumnNamefromId(albums_id)
	return render_template('photos.html', albums=AlbumName, photos=photos_list)

@app.route('/album/<albums_id>', methods=['GET'])
@flask_login.login_required
def showPhotos(albums_id):
	photos_list=findPhotosInAlbums(albums_id)
	AlbumName=findAlbumnNamefromId(albums_id)
	return render_template('photos.html', name=flask_login.current_user.id, albums=AlbumName, photos=photos_list)

@app.route('/deleteAlbum', methods=['POST'])
@flask_login.login_required
def deleteAlbum():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	albums_id=request.args.get('values')
	albumn_user_id = findAlbumUserID(albums_id)
	if albumn_user_id == uid:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM Albums WHERE albums_id = '{0}'".format(albums_id))
		conn.commit()
		uid=getUserIdFromEmail(flask_login.current_user.id)
		cursor.execute("SELECT albums_id, albums_name, date_of_creation FROM Albums WHERE Users_user_id = '{0}'".format(uid))
		Albums_list= cursor.fetchall()
		return render_template('albums.html', name=flask_login.current_user.id, message='Album deleted', albums=Albums_list)
	else:
		return render_template('profile.html', name=flask_login.current_user.id, message='Wrong User!')


def getAllPhotos():
	cursor = conn.cursor()
	cursor.execute("SELECT photos_id ,photos_path, caption FROM Pictures")
	return cursor.fetchall()

def getAllAlbums():
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, albums_name, firstname FROM Albums, Users WHERE Albums.Users_user_id = Users.user_id")
	return cursor.fetchall()

def findUserAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id,albums_name, date_of_creation FROM Albums WHERE Users_user_id = '{0}'".format(uid))
	return cursor.fetchall()

def findAlbumUserID(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Users_user_id FROM Albums WHERE albums_id = '{0}'".format(albums_id))
	return cursor.fetchone()[0]

def findAlbumIdFromName(AlbumName):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id From Albums Where albums_name = '{0}'".format(AlbumName))
	return cursor.fetchone()[0]

def findAlbumnNamefromId(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_name FROM Albums WHERE albums_id = '{0}'".format(albums_id))
	return cursor.fetchone()[0]

def findPhotosInAlbums(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT photos_id, photos_path, caption FROM Pictures WHERE Albums_albums_id = '{0}'".format(albums_id))
	return cursor.fetchall()

def findPhotoId(photos_path, caption, albums_id):
	cursor = conn.cursor()
	sql = '''SELECT photos_id FROM Pictures WHERE photos_path = %s AND caption = %s AND Albums_albums_id = %s'''
	data = (photos_path, caption, albums_id, )
	cursor.execute(sql, data)
	return cursor.fetchone()[0]

def isTagUnique(tags_text):
	cursor = conn.cursor()
	if cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags WHERE Tags_tags_text = '{0}'".format(tags_text)):
		return False
	else:
		return True

def isTagAlreadyExist(tags_text):
	cursor = conn.cursor()
	if cursor.execute("SELECT tags_text FROM Tags WHERE tags_text = '{0}'".format(tags_text)):
		return True
	else:
		return False

@app.route('/deletePhoto', methods=['POST'])
@flask_login.login_required
def deletePhoto():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos_id=request.args.get('values')
	photos_owner_id=findPhotoOwnerId(photos_id)
	cursor = conn.cursor()
	if photos_owner_id == uid:
		cursor.execute("DELETE FROM Pictures WHERE photos_id = '{0}'".format(photos_id))
		conn.commit()
		AlbumName=request.args.get('AlbumName')
		albums_id=findAlbumIdFromName(AlbumName)
		photos_list=findPhotosInAlbums(albums_id)
		return render_template('photos.html', message='Photo deleted', photos=photos_list)
	else:
		return render_template('profile.html', name=flask_login.current_user.id, message='Wrong User!')


# For explores
def findAllPhotoIdFromTag(tags_text):
	cursor = conn.cursor()
	cursor.execute("SELECT Photos_photos_id FROM Photos_has_Tags, Pictures WHERE Photos_has_Tags.Photos_photos_id = Pictures.photos_id AND Photos_has_Tags.Tags_tags_text = '{0}'".format(tags_text))
	return cursor.fetchall()

def findAlbumnNamefromId(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_name FROM Albums WHERE albums_id = '{0}'".format(albums_id))
	return cursor.fetchone()[0]

def findPhotoOwnerId(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT photos_owner_id FROM Pictures WHERE photos_id = '{0}'".format(photos_id))
	return cursor.fetchone()[0]

def findAllPhotoPathFromId(photos_id):
	albums_id = findAlbumIdFromPhotoId(photos_id)
	cursor = conn.cursor()
	cursor.execute("SELECT photos_path, caption, albums_name FROM Pictures, Albums WHERE photos_id = '{0}' AND albums_id = '{1}'".format(photos_id, albums_id))
	return cursor.fetchone()

def findAlbumIdFromPhotoId(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Albums_albums_id FROM Pictures WHERE photos_id = '{0}'".format(photos_id))
	return cursor.fetchone()[0]

def isTagUnique(tags_text):
	cursor = conn.cursor()
	if cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags WHERE Tags_tags_text = '{0}'".format(tags_text)):
		return False
	else:
		return True

def isTagAlreadyExist(tags_text):
	cursor = conn.cursor()
	if cursor.execute("SELECT tags_text FROM Tags WHERE tags_text = '{0}'".format(tags_text)):
		return True
	else:
		return False

def findPhotoPathFromId(photos_id):
	uid=getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT photos_path, caption, albums_name, photos_owner_id FROM Pictures, Albums WHERE photos_id = '{0}' AND photos_owner_id = '{1}' AND Users_user_id = '{2}'".format(photos_id, uid, uid))
	return cursor.fetchone()

def findPhotoIdFromTag(tags_text, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT Photos_photos_id FROM Photos_has_Tags, Pictures WHERE Photos_has_Tags.Photos_photos_id = Pictures.photos_id AND Photos_has_Tags.Tags_tags_text = '{0}' AND Pictures.photos_owner_id = '{1}'".format(tags_text, uid))
	return cursor.fetchall()

def findTagsinPhoto(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags WHERE Photos_photos_id = '{0}'".format(photos_id))
	return cursor.fetchall()

def findPhotoId(photos_path, caption, albums_id):
	cursor = conn.cursor()
	sql = "SELECT photos_id FROM Pictures WHERE photos_path = %s AND caption = %s AND Albums_albums_id = %s"
	data = (photos_path, caption, albums_id,)
	cursor.execute(sql, data)
	return cursor.fetchone()[0]

def findAlbumUserID(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Users_user_id FROM Albums WHERE albums_id = '{0}'".format(albums_id))
	return cursor.fetchone()[0]

def findPhotosInAlbums(albums_id):
	cursor = conn.cursor()
	cursor.execute("SELECT photos_id, photos_path, caption FROM Pictures WHERE Albums_albums_id = '{0}'".format(albums_id))
	return cursor.fetchall()

def findUserAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id,albums_name, date_of_creation FROM Albums WHERE Users_user_id = '{0}'".format(uid))
	return cursor.fetchall()

def findAlbumIdFromName(AlbumName):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id From Albums Where albums_name = '{0}'".format(AlbumName))
	return cursor.fetchone()[0]



@app.route('/top10Users', methods=['GET'])
@flask_login.login_required
def top10Users():
	top10UsersId=showTop10User()
	top10UsersInfo=[]
	for i in top10UsersId:
		cursor = conn.cursor()
		cursor.execute("SELECT firstname, email FROM Users WHERE user_id = '{0}'".format(i))
		top10UsersInfo.append(cursor.fetchone())
	return render_template('top10Users.html', results=top10UsersInfo)

def showTop10User():
	user_contribution = getContribution()
	resultId=[]
	resultlist = sorted(user_contribution, key=Key)
	tmp = []
	for i in range(len(resultlist)):
		if resultlist[i][0] != None:
			tmp.append(resultlist[i])
	if len(tmp) <= 10:
		for j in tmp:
			resultId.append(j[0])
		return resultId
	else:
		toplist=tmp[-9:]
		for k in toplist:
			resultId.append(k[0])
		return resultId

def Key(item):
	return item[1]

def getContribution():
	user_contribution = []
	cursor = conn.cursor()
	cursor.execute("SELECT C.comment_owner_id, count(comment_owner_id) FROM Comments AS C GROUP BY C.comment_owner_id")
	for i in cursor:
		user_contribution.append([i[0], i[1]])
	cursor = conn.cursor()
	cursor.execute("SELECT P.photos_owner_id, count(photos_owner_id) FROM Pictures AS P GROUP BY P.photos_owner_id")
	for j in cursor:
		for k in user_contribution:
			if j[0] == k[0]:
				k[1] = k[1]+j[1]
			else:
				k[1] = k[1]
	return user_contribution


@app.route('/comments/<commentPhotoId>', methods=['GET'])
def viewComments(commentPhotoId):
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		cursor = conn.cursor()
		cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments FROM Comments WHERE Photos_photos_id = '{0}'".format(commentPhotoId))
		comments_list=cursor.fetchall()
		return render_template('comments.html', name=flask_login.current_user.id, message="Here are the comments of this photo", comments= comments_list, photoID=commentPhotoId)
	except:
		cursor = conn.cursor()
		cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments FROM Comments WHERE Photos_photos_id = '{0}'".format(commentPhotoId))
		comments_list=cursor.fetchall()
		return render_template('comments.html', message="Here are the comments of this photo", comments= comments_list, photoID=commentPhotoId)

@app.route('/searchComments', methods=['GET'])
def searchComments():
	query = request.args.get('query')
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Comments WHERE comments_text LIKE %s", ("%" + query + "%",))
	comments_list = cursor.fetchall()
	users_with_comment_count = [[], []]
	for i in comments_list:
		if i[2] in users_with_comment_count[1]:
			users_with_comment_count[0][users_with_comment_count[1].index(i[2])] += 1
		else:
			users_with_comment_count[0].append(1)
			users_with_comment_count[1].append(i[2])
	sorted_users = []
	for i in range(len(users_with_comment_count[0])):
		sorted_users.append([users_with_comment_count[0][i], users_with_comment_count[1][i]])
	sorted_users = sorted(sorted_users, reverse=True)
	return render_template('searchComments.html', query=query, comments=comments_list, users=sorted_users)


@app.route('/comments/addComment/<photoID>', methods=['GET'])
@flask_login.login_required
def comments(photoID):
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('comments.html', message="Leave a comment!", addComment="True", name=flask_login.current_user.id, photoID=photoID)
	except:
		return render_template('comments.html', message="Leave a comment!", addComment="True", photoID=photoID)

@app.route('/leaveComments/<photoID>', methods=['POST'])
def leaveComments(photoID):
	comments_text=request.form.get('comment')
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		comments_owner_name = findUserNameFromId(uid)
	except:
		uid = None
		comments_owner_name = 'Visitor'
	date_of_comments= time.strftime("%Y-%m-%d")
	photos_owner_id=findPhotoOwnerId(photoID)
	if photos_owner_id==uid:
		comments_list=findCommentFromPhotoId(photoID)
		return render_template ('comments.html', message='You can\'t leave a comment in your own photo', comments=comments_list, name=flask_login.current_user.id)
	if uid == None:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments(comments_text, comments_owner_name, date_of_comments, Photos_photos_id) VALUES ('{0}', '{1}', '{2}', '{3}')".format(comments_text, comments_owner_name, date_of_comments, photoID))
		conn.commit()
	else:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Comments(comments_text, comments_owner_name, date_of_comments, Photos_photos_id, comment_owner_id) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')".format(comments_text, comments_owner_name, date_of_comments, photoID, uid))
		conn.commit()
	comments_list=findCommentFromPhotoId(photoID)
	try:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('comments.html', message="Comment created!", name=flask_login.current_user.id, comments=comments_list, photoID=photoID)
	except:
		return render_template('comments.html', message="Comment created!", comments=comments_list, photoID=photoID)


def findCommentFromPhotoId(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT comments_text, comments_owner_name, date_of_comments, comments_id FROM Comments WHERE Photos_photos_id = '{0}'".format(photos_id))
	return cursor.fetchall()

def findUserNameFromId(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT firstname FROM Users WHERE user_id = '{0}'".format(uid))
	return cursor.fetchone()[0]


@app.route('/tags/<photos_id>', methods=['GET'])
def showTags(photos_id):
	tags_fetch=findTagsinPhoto(photos_id)
	tags_list=[]
	for i in range(len(tags_fetch)):
		tags_list.append(tags_fetch[i][0])
	return render_template('tags.html', message="Here are the tags of this photo", tags=tags_list)

@app.route('/yourOtherPhotos/<tags_text>', methods=['GET'])
@flask_login.login_required
def UserPhotoswithTag(tags_text):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos_fetch=findPhotoIdFromTag(tags_text, uid)
	photos_id_list=[]
	for i in range(len(photos_fetch)):
		photos_id_list.append(photos_fetch[i][0])
	photos_list=[]
	for j in range(len(photos_id_list)):
		photos_list.append(findPhotoPathFromId(photos_id_list[j]))
	return render_template('viewbytags.html', name=flask_login.current_user.id, message="Here are your photos with this tag", photos=photos_list, tags=tags_text)

@app.route('/peoplePhotoswithTag', methods=['POST'])
@flask_login.login_required
def peoplePhotoswithTag():
	tags_text =request.args.get('values')
	photos_fetch=findAllPhotoIdFromTag(tags_text)
	photos_id_list=[]
	for i in range(len(photos_fetch)):
		photos_id_list.append(photos_fetch[i][0])
	photos_list=[]
	for j in range(len(photos_id_list)):
		photos_list.append(findAllPhotoPathFromId(photos_id_list[j]))
	return render_template('viewbytags.html', name=flask_login.current_user.id, message="Here are all the photos with this tag", photos=photos_list, tags=tags_text, checked="True")

@app.route('/tags/populartags', methods=['GET'])
@flask_login.login_required
def populartags():
	cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags AS PT, Pictures AS P WHERE PT.Photos_photos_id = photos_id GROUP BY PT.Tags_tags_text order by count(P.photos_id) desc limit 5")
	populartags_list_fetch = cursor.fetchall()
	populartags_list=[]
	for i in range(len(populartags_list_fetch)):
		populartags_list.append(populartags_list_fetch[i][0])
	if populartags_list:
		return render_template('tags.html', tags=populartags_list, name=flask_login.current_user.id, message="Here are the popular tags that people use right now.")
	else:
		return render_template('tags.html', name=flask_login.current_user.id, message="No tag found on this site yet, this is your opportunity to be the first")


@app.route('/showTagsSearchResult', methods=['post'])
def showTagsSearchResult():
	searchTags=request.form.get('search')
	tags_list=searchTags.split(" ")
	resultPhotoPath=[]
	if len(tags_list) == 1:
		resultPhotoId=findAllPhotoIdFromTag(tags_list[0])
		for i in range(len(resultPhotoId)):
			resultPhotoPath.append(findAllPhotoPathFromId(resultPhotoId[i][0]))
		return render_template('viewbyTags.html', message="Here are the search result", results=tags_list, photos=resultPhotoPath)
	else:
		resultPhotoId = []
		for i in range(len(tags_list)):
			a = findAllPhotoIdFromTag(tags_list[i])
			tmp = []
			for j in range(len(a)):
				tmp.append(a[j][0])
			resultPhotoId.append(tmp)
		tmp = resultPhotoId[0]
		commonPhotoId = []
		tmp2 = resultPhotoId[1:]
		for k in range(len(tmp)):
			flag=True
			for h in range(len(tmp2)):
				if tmp[k] in tmp2[h]:
					continue
				else:
					flag=False
					break
			if flag == True:
				commonPhotoId.append(tmp[k])
		for i in range(len(commonPhotoId)):
			resultPhotoPath.append(findAllPhotoPathFromId(commonPhotoId[i]))
		return render_template('viewbyTags.html', message="Here are the search result", results=tags_list, photos=resultPhotoPath)

@app.route('/likes/<photos_id>', methods=['GET'])
@flask_login.login_required
def likes(photos_id):
	cursor = conn.cursor()
	cursor.execute("SELECT User_of_like FROM Can_Likes WHERE photos_id='{0}'".format(photos_id))
	userliked_list=cursor.fetchall()
	cursor.execute("SELECT count(User_of_like) FROM Can_Likes WHERE photos_id = '{0}'".format(photos_id))
	numberoflike = cursor.fetchall()[0]
	cursor.execute("SELECT * FROM Can_Likes WHERE User_of_like = %s AND photos_id = %s", (findUserNameFromId(getUserIdFromEmail(flask_login.current_user.id)), photos_id))
	isLiked = False
	if cursor.fetchone():
		isLiked = True
	return render_template('likes.html', message="See who like this photo", users=userliked_list, photoID=photos_id, number=numberoflike, liked=isLiked)

@app.route('/likes/<photos_id>', methods=['POST'])
@flask_login.login_required
def clickLikes(photos_id):
	uid=getUserIdFromEmail(flask_login.current_user.id)
	user_firstname=findUserNameFromId(uid)
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Can_Likes WHERE User_of_like = %s AND photos_id = %s", (user_firstname, photos_id))
	isLiked = False
	if cursor.fetchone():
		isLiked = True
	if isLiked:
		cursor.execute("DELETE FROM Can_Likes WHERE User_of_like = %s AND photos_id = %s", (user_firstname, photos_id))
	else:
		cursor.execute("INSERT INTO Can_Likes(User_of_like, photos_id) VALUES ('{0}', '{1}')".format(user_firstname, photos_id))
	conn.commit()
	cursor.execute("SELECT User_of_like FROM Can_Likes WHERE photos_id='{0}'".format(photos_id))
	userliked_list=cursor.fetchall()
	cursor.execute("SELECT count(User_of_like) FROM Can_Likes WHERE photos_id = '{0}'".format(photos_id))
	numberoflike = cursor.fetchall()[0]
	return render_template('likes.html', message="See who like this photo", users=userliked_list, photoID=photos_id, number=numberoflike, liked=isLiked)


@app.route('/youmayalsolike/<user_id>', methods=['GET'])
@flask_login.login_required
def youmayalsolike(user_id):
	populartags_list= findUserPopularTags(user_id)
	cursor=conn.cursor()
	cursor.execute("SELECT photos_id from Pictures")
	photos_id_list=cursor.fetchall()
	rank = {}
	for i in photos_id_list:
		for j in populartags_list:
			cursor=conn.cursor()
			cursor.execute("SELECT P.photos_id from Pictures p, Photos_has_Tags PT where PT.Tags_tags_text= '{0}' AND PT.Photos_photos_id= '{1}' AND PT.Photos_photos_id=P.photos_id".format(j,i[0]))
			rank_list=cursor.fetchall()
			for k in rank_list:
				if k[0] not in rank:
					rank[k[0]] = 1
				else:
					rank[k[0]]+=1
	sorted_rank = sorted(rank.items(), key=operator.itemgetter(1), reverse=True)
	photos_list = ()
	for key, value in sorted_rank:
		cursor = conn.cursor()
		cursor.execute("SELECT photos_id, photos_path, caption FROM Pictures WHERE photos_id = '{0}'".format(key))
		photos_list += cursor.fetchall()
	return render_template('/youmayalsolike.html', photos=photos_list, tags=populartags_list)

@app.route('/tags/recommands', methods=['GET'])
@flask_login.login_required
def tagrecommands():
	return render_template('tagRecommand.html')

@app.route('/tag/searchResult', methods=['POST'])
@flask_login.login_required
def recommandTags():
	searchTags = request.form.get("search")
	inputTags_list = searchTags.split(" ")
	cursor = conn.cursor()
	cursor.execute("SELECT tags_text FROM Tags")
	tags_list = cursor.fetchall()
	actualTags = []
	for i in inputTags_list:
		cursor = conn.cursor()
		cursor.execute("SELECT tags_text FROM Tags WHERE tags_text = '{0}' AND tags_text IN (SELECT tags_text FROM Tags)".format(i))
		actualTags.append(cursor.fetchall())
	photos_list=[]
	flag = True
	for b in actualTags:
		if b != ():
			flag= False
	if flag == True:
		return render_template("tagRecommand.html", message="No related tags")
	for i in range(len(actualTags)):
		if actualTags[i] == ():
			actualTags.pop()
	for j in actualTags:
		cursor = conn.cursor()
		cursor.execute("SELECT Photos_photos_id FROM Photos_has_Tags WHERE Tags_tags_text = '{0}'".format(j[0][0]))
		photos_list.append(cursor.fetchall())
	photo_taglist = []
	for k in photos_list:
		for m in range(len(k)):
			cursor = conn.cursor()
			cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags WHERE Photos_photos_id = '{0}'".format(k[m][0]))
			photo_taglist.append(cursor.fetchall())
	rank = {}
	for n in photo_taglist:
		for r in range(len(n)):
			if n[r][0] not in rank:
				rank[n[r][0]] = 1
			else:
				rank[n[r][0]] += 1
	for a in actualTags:
		rank.pop(a[0][0], None)
	sorted_rank = sorted(rank.items(), key=operator.itemgetter(1), reverse=True)
	return render_template('tagRecommand.html', tags=sorted_rank)

def turnIntoString(relatedPhoto_fetch):
	tmp = ''
	for i in relatedPhoto_fetch:
		tmp = tmp + str(i) + ','
	return tmp[0:len(tmp)-1]

def findUserPopularTags(user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Tags_tags_text FROM Photos_has_Tags AS PT, Pictures AS P WHERE PT.Photos_photos_id = photos_id AND P.photos_owner_id = '{0}' GROUP BY PT.Tags_tags_text order by count(P.photos_id) desc limit 5".format(user_id))
	populartags_list_fetch = cursor.fetchall()
	populartags_list=[]
	for i in range(len(populartags_list_fetch)):
		populartags_list.append(populartags_list_fetch[i][0])
	return populartags_list



#default page
@app.route("/", methods=['GET'])
def hello():
	photo = getAllPhotos()
	album = getAllAlbums()
	return render_template('hello.html', message='Welcome to Photoshare', photos=photo, albums=album)


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
