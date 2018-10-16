from flask import Flask, render_template, redirect, request, url_for, \
    flash, jsonify

# import CRUD Operations
from database_setup import Base, User, Subject, Topic, Question
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Auth imports
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
# Markdown
import markdown
from flask import Markup
# Find files
import os

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Create session and connect to DB ##
engine = create_engine('sqlite:///educationmenu.db')
Base.metadata.bind = engine

session = scoped_session(sessionmaker(bind=engine))

app = Flask(__name__)

@app.route('/users')
@app.route('/users/')
def users():
    users = session.query(User)
    # return "The current session state is %s" % login_session['state']
    return(render_template('users.html', users=users))

# Create anti-forgery state token
@app.route('/login')
@app.route('/login/')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return(render_template('login.html', STATE=state))


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return(response)
    access_token = request.data
    print("access token received {token} ".format(token=access_token))


    app_id = json.loads(open('fb_client_secrets.json', 'r').read())\
    ['web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = "https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={client_id}&client_secret={client_secret}&fb_exchange_token={fb_exchange_token}"\
    .format(client_id = app_id, client_secret = app_secret, fb_exchange_token = access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v3.1/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = "https://graph.facebook.com/v3.1/me?access_token={token}&fields=name,id,email".format(token=token)

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result

    data = json.loads(result)
    print('data: {}'.format(data))
    login_session['provider'] = 'facebook'
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['facebook_id'] = data['id']

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token={token}&redirect=0&height=200&width=200'.format(token=token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # User Helper Functions

    def getUserID(email):
        try:
            user = session.query(User).filter_by(email=email).one()
            return user.id
        except:
            return None

    def createUser(login_session):
        newUser = User(name=login_session['username'], email=login_session[
                       'email'], picture=login_session['picture'])
        session.add(newUser)
        session.commit()
        user = session.query(User).filter_by(email=login_session['email']).one()
        return user.id

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as {username}".format(username=login_session['username']))

    return(output)


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/{fb_id}/permissions?access_token={access_token}'.format(fb_id=facebook_id,access_token=access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return("you have been logged out")


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return(response)
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return(response)

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}'.format(token=access_token))
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return(response)

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return(response)

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return(response)

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return(response)

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    def createUser(login_session):
        newUser = User(name=login_session['username'], email=login_session[
                       'email'], picture=login_session['picture'])
        session.add(newUser)
        session.commit()
        user = session.query(User).filter_by(email=login_session['email']).one()
        return(user.id)


    def getUserInfo(user_id):
        user = session.query(User).filter_by(id=user_id).one()
        return(user)


    def getUserID(email):
        try:
            user = session.query(User).filter_by(email=email).one()
            return(user.id)
        except:
            return(None)

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # See if a user exists, if it doesn't make a new one

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as {username}".format(username=login_session['username']))
    print("done!")
    return(output)

@app.route('/gdisconnect')
@app.route('/gdisconnect/')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%{token}'.format(token=access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return(redirect(url_for('subjects')))
    else:
        flash("You were not logged in")
        return(redirect(url_for('subjects')))


@app.route('/')
@app.route('/education')
@app.route('/education/')
def subjects():
    subjects = session.query(Subject)
    return(render_template('subjects.html', subjects=subjects, login_session=login_session))

@app.route('/education/subject/new', methods=['GET', 'POST'])
@app.route('/education/subject/new/', methods=['GET', 'POST'])
def newSubject():
    if request.method == 'POST':
        newSubject = Subject(name=request.form['name'])
        session.add(newSubject)
        session.commit()
        flash("New subject created!")
        return(redirect(url_for('subjects')))
    else:
        return(render_template('newsubject.html'))


@app.route('/education/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@app.route('/education/subject/<int:subject_id>/edit/', methods=['GET', 'POST'])
def editSubject(subject_id):
    editSubject = session.query(Subject).filter_by(id=subject_id).one()
    if request.method == 'POST':
        editSubject.name = request.form['name']
        session.add(editSubject)
        session.commit()
        flash("Subject edited")
        return(redirect(url_for('subjects')))
    else:
        return(render_template('editsubject.html',subject=editSubject,login_session=login_session))


@app.route('/education/subject/<int:subject_id>/delete',
           methods=['GET', 'POST'])
@app.route('/education/subject/<int:subject_id>/delete/',
           methods=['GET', 'POST'])
def deleteSubject(subject_id):
    deleteSubject = session.query(Subject)\
	                .filter_by(id=subject_id).one()
    if request.method == 'POST':
        session.delete(deleteSubject)
        session.commit()
        flash("Subject deleted!")
        return(redirect(url_for('subjects')))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletesubject.html', subject=subject))


@app.route('/education/<int:subject_id>', methods=['GET', 'POST'])
@app.route('/education/<int:subject_id>/', methods=['GET', 'POST'])
def topics(subject_id):
    topics = session.query(Topic).filter_by(subject_id=subject_id)
    subject = session.query(Subject).filter_by(id=subject_id).one()
    subjects = session.query(Subject)
    return(render_template('topics.html', topics=topics, subject=subject,login_session=login_session,subjects=subjects))


@app.route('/education/<int:subject_id>/JSON')
def subjectJSON(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    topics = session.query(Topic).filter_by(subject_id=subject.id)
    return(jsonify(topics=[topics.serialize for topic in topics]))


@app.route('/education/<int:subject_id>/<int:topic>', methods=['GET', 'POST'])
@app.route('/education/<int:subject_id>/<int:topic>/', methods=['GET', 'POST'])
def topic(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    return(render_template('topic.html', subject=subject))

@app.route('/education/<int:subject_id>/<int:topic_id>/view', methods=['GET'])
@app.route('/education/<int:subject_id>/<int:topic_id>/view/', methods=['GET'])
def viewTopic(subject_id,topic_id):
    topic = session.query(Topic).filter_by(id=topic_id)
    article = topic.one().article
    with open('./static/articles/{article}'.format(article=article), 'r') as file:
        content = file.read()
        content = Markup(markdown.markdown(content))
    subject = session.query(Subject).filter_by(id=subject_id).one()
    return(render_template('topic.html', subject=subject,login_session=login_session, content=content))


@app.route('/education/<int:subject_id>/topic/new', methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/new/', methods=['POST', 'GET'])
def newTopic(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    if request.method == 'POST':
        newTopic = Topic(
            name=request.form['name'], description=request.form['description'],\
			subject_id=subject_id)
        session.add(newTopic)
        session.commit()
        flash("New topic created!")
        return(redirect(url_for('topics', subject_id=subject_id)))
    else:
        return(render_template('newtopic.html', subject=subject))


@app.route('/education/<int:subject_id>/topic/<int:topic_id>/edit',
           methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/<int:topic_id>/edit/',
          methods=['POST', 'GET'])
def editTopic(subject_id, topic_id):
    files = os.listdir('./static/articles')
    editTopic = session.query(Topic).filter_by(subject_id=subject_id,
                                              id=topic_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editTopic.name = request.form['name']
            editTopic.description = request.form['description']
            editTopic.article = request.form['article']
            session.add(editTopic)
            session.commit()
            flash("Subject topic edited!")
        return(redirect(url_for('topics', subject_id=subject_id,login_session=login_session)))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('edittopic.html', subject=subject,
                               topic=editTopic,login_session=login_session,files=files))


@app.route('/education/<int:subject_id>/topic/<int:topic_id>/delete',
           methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/<int:topic_id>/delete/',
          methods=['POST', 'GET'])
def deleteTopic(subject_id, topic_id):
    deleteTopic = session.query(Topic).filter_by(subject_id=subject_id,
                                                   id=topic_id).one()
    if request.method == 'POST':
        session.delete(deleteTopic)
        session.commit()
        flash("Topic deleted!")
        return(redirect(url_for('topics', subject_id=subject_id)))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletetopic.html', subject=subject,
                               topic=deleteTopic))

if __name__ == '__main__':
    app.secret_key = 'supersecretkey'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
