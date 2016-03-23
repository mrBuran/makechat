"""All logic of user login/registration is should be described here."""

import uuid
import hashlib
import falcon

from mongoengine.errors import ValidationError

from makechat.models import User, Session
from makechat.api.utils import max_body
from makechat import config as settings


SESSION_TTL = settings.getint('DEFAULT', 'session_ttl')
SECRET_KEY = settings.get('DEFAULT', 'secret_key')


class UserRegister:
    """User register API endpoint."""

    @falcon.before(max_body(1024))
    def on_post(self, req, resp):
        """Process POST request from /register.html form."""
        payload = req.context['payload']
        try:
            email = payload['email']
            username = payload['username']
            password1 = payload['password1']
            password2 = payload['password2']
        except KeyError as er:
            raise falcon.HTTPBadRequest('Missing parameter',
                                        'The %s parameter is required.' % er)
        if password1 != password2:
            raise falcon.HTTPBadRequest('Bad password',
                                        'Passwords do not match.')
        if User.objects.filter(username=username):
            raise falcon.HTTPBadRequest('Bad username',
                                        'Username is already taken.')
        if User.objects.filter(email=email):
            raise falcon.HTTPBadRequest('Bad email',
                                        'Email is already taken.')
        try:
            password = hashlib.sha256(
                password1.encode('ascii') + SECRET_KEY.encode('ascii')
            ).hexdigest()
            session = Session()
            session.value = hashlib.sha256(
                username.encode('ascii') +
                uuid.uuid4().hex.encode('ascii')
            ).hexdigest()
        except UnicodeEncodeError:
            raise falcon.HTTPBadRequest('Bad password symbols',
                                        'Invalid password characters.')
        try:
            user = User.objects.create(
                username=username, password=password, email=email)
        except ValidationError as er:
            raise falcon.HTTPBadRequest('Error of user creation',
                                        '%s' % er.to_dict())
        session.user = user
        session.save()
        resp.set_cookie('session', session.value, path='/', secure=False,
                        max_age=SESSION_TTL)
        resp.status = falcon.HTTP_201


class UserLogin:
    """User login API endpoint."""

    def on_get(self, req, resp):
        """Process GET requests for /login.html."""
        cookies = req.cookies
        if 'session' not in cookies:
            raise falcon.HTTPUnauthorized('Not authentificated',
                                          'Please login.')
        if not Session.objects.with_id(cookies['session']):
            raise falcon.HTTPUnauthorized('Not authentificated',
                                          'Please login.')
        resp.status = falcon.HTTP_200

    @falcon.before(max_body(1024))
    def on_post(self, req, resp):
        """Process POST request from /login.html form."""
        payload = req.context['payload']
        try:
            username = payload['username']
            password = payload['password']
        except KeyError as er:
            raise falcon.HTTPBadRequest('Missing parameter',
                                        'The %s parameter is required.' % er)
        try:
            password = hashlib.sha256(
                password.encode('ascii') + SECRET_KEY.encode('ascii')
            ).hexdigest()
        except UnicodeEncodeError:
            raise falcon.HTTPUnauthorized('Bad password symbols',
                                          'Invalid password characters.')
        try:
            user = User.objects.get(username=username, password=password)
        except User.DoesNotExist:
            raise falcon.HTTPUnauthorized('Bad login attempt',
                                          'Invalid username or password.')
        session = Session()
        session.value = hashlib.sha256(
            username.encode('ascii') +
            uuid.uuid4().hex.encode('ascii')
        ).hexdigest()
        session.user = user
        session.save()
        resp.set_cookie('session', session.value, path='/', secure=False,
                        max_age=SESSION_TTL)
        resp.status = falcon.HTTP_200
