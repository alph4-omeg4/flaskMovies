import datetime
from functools import wraps

import jwt
from flask import request, jsonify
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from src import db, app
from src.database.models import User
from src.schemas.user import UserSchema


class AuthRegister(Resource):
    user_schema = UserSchema()

    def post(self):
        try:
            user = self.user_schema.load(request.json, session=db.session)
        except ValidationError as e:
            return {'message': str(e)}
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError as ie:
            db.session.rollback()
            return {'message': "User exists"}, 409, ie
        except ValidationError as e:
            return {'message': str(e)}
        return self.user_schema.dump(user), 201


# curl -d '{"username":"TEST9", "email":"9email@mail.ru", "password":"111"}' -H "Content-Type: application/json" -X POST http://localhost:5000/register


class AuthLogin(Resource):
    def get(self):
        auth = request.authorization
        if not auth:
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        user = User.find_user_by_username(auth.get('username', ''))
        if not user or not check_password_hash(user.password, auth.get('password', '')):
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        token = jwt.encode(
            {
                "user_id": user.uuid,
                "exp": datetime.datetime.now() + datetime.timedelta(minutes=10)
            }, app.config['SECRET_KEY'],
            algorithm="HS256"
        )
        # return token
        return jsonify(
            {
                "token": token
            }
        )


def token_required(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        token = request.headers.get('X-API-KEY', '')
        if not token:
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        try:
            uuid = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")['user_id']
            # return uuid
        except (KeyError, jwt.ExpiredSignatureError):
            # jwt.InvalidSignatureError
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        user = User.find_user_by_uuid(uuid)
        if not user:
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        return func(self, *args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        token = request.headers.get('X-API-KEY', '')
        if not token:
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        try:
            uuid = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")['user_id']
            # return uuid
        except (KeyError, jwt.ExpiredSignatureError):
            # jwt.InvalidSignatureError
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        user = db.session.query(User).filter_by(uuid=uuid).first()
        if not user:
            return "", 401, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        if not user.is_admin:
            return "", 403, {"WWW-Authenticate": "Basic realm='Authentication required'"}
        return func(self, *args, **kwargs)
    return wrapper
