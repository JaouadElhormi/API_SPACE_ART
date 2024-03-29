from flask import request, Blueprint, g
from .mailController import login_success,randomString
from ..models.UserModel import UserModel, UserSchema
from ..models.ProfileModel import ProfileModel
from ..models.NotifModel import NotifModel
from ..models.RevokedTokenModel import RevokedTokenModel
from src.jsonResponse import custom_response
from ..shared.Authentication import Auth
from ..Google_storage import google

user_api = Blueprint('users', __name__)
user_schema = UserSchema()

@user_api.route('/create', methods=['POST'])
def create():
    req_data = request.get_json()
    data, error = user_schema.load(req_data)
    if error:
        return custom_response(error, 400)
    user_in_db = UserModel.get_user_by_email(data.get('email'))
    if user_in_db or data.get('email') == google.google_unauthorized:
        return custom_response({'error': 'User already exist, please supply another email address'}, 400)
    random_key = randomString(4)
    mail_exist = login_success('login.html', data.get('email'), random_key)
    if mail_exist == 0:
        return custom_response({'error': 'Email address not found'}, 400)
    user = UserModel(data, 0, random_key + "-0")
    user.save()
    NotifModel.init_by_user_id(user.id)
    profile = ProfileModel({}, user.id)
    profile.save()
    return custom_response({'success': 'User created'}, 201)


@user_api.route('/all', methods=['GET'])
def get_all():
    users = UserModel.get_all_users()
    ser_users = user_schema.dump(users, many=True).data
    return custom_response(ser_users, 200)


@user_api.route('/get_users_like/<string:string_like>', methods=['GET'])
def get_users_like(string_like):
    users_lastname = UserModel.get_users_lastname_like(string_like)
    users_firstname = UserModel.get_users_firstname_like(string_like)
    for u_l in users_lastname:
        for u_f in users_firstname:
            if u_l.email == u_f.email:
                users_firstname.remove(u_f)
    list_users = users_lastname + users_firstname
    ser_users = user_schema.dump(list_users, many=True).data
    return custom_response(ser_users, 200)


@user_api.route('/get_users_lastname_like/<string:string_like>', methods=['GET'])
def get_users_lastname_like(string_like):
    users = UserModel.get_users_lastname_like(string_like)
    ser_users = user_schema.dump(users, many=True).data
    return custom_response(ser_users, 200)


@user_api.route('/get_users_firstname_like/<string:string_like>', methods=['GET'])
def get_users_firstname_like(string_like):
    users = UserModel.get_users_firstname_like(string_like)
    ser_users = user_schema.dump(users, many=True).data
    return custom_response(ser_users, 200)


@user_api.route('/get_users_email_like/<string:string_like>', methods=['GET'])
def get_users_email_like(string_like):
    users = UserModel.get_users_email_like(string_like)
    ser_users = user_schema.dump(users, many=True).data
    return custom_response(ser_users, 200)


@user_api.route('/mail_validate', methods=['POST'])
@Auth.auth_required
def mail_validate():
    req_data = request.get_json()
    users = UserModel.get_one_user(g.user.get('id'))
    tab_validate = list(user_schema.dump(users).data.get('mail_validate'))
    del(tab_validate[5])
    del(tab_validate[4])
    string_validate = "".join(tab_validate)
    print(string_validate + "     " + req_data.get('key_mail'))
    if string_validate == req_data.get('key_mail'):
        users.update_mail("0000-1")
        return custom_response({'success': 'Code valid'}, 200)
    return custom_response({'error': 'Code not valid.'}, 400)

@user_api.route('/private_user', methods=['GET'])
@Auth.auth_required
def private_user():
    user = UserModel.get_one_user(g.user.get('id'))
    user.update_private(1)
    return custom_response({'success': 'Code not valid.'}, 200)


@user_api.route('/public_user', methods=['GET'])
@Auth.auth_required
def public_user():
    user = UserModel.get_one_user(g.user.get('id'))
    user.update_private(0)
    return custom_response({'success': 'Code not valid.'}, 200)


@user_api.route('/user_to_admin/<int:user_id>', methods=['PUT'])
@Auth.auth_required
def user_to_admin(user_id):
    user_admin = UserModel.get_one_user(g.user.get('id'))
    ser_users_admin = user_schema.dump(user_admin).data
    if ser_users_admin.get('right') == 2:
      user_change = UserModel.get_one_user(user_id)
      ser_users_change = user_schema.dump(user_change).data
      if ser_users_change.get('right') == 0:
          user_change.update_right(1)
          return custom_response({'Change': 'user_to_admin'}, 200)
      elif ser_users_change.get('right') == 1:
          user_change.update_right(0)
          return custom_response({'Change': 'admin_to_user'}, 200)
      return custom_response({'Unauthorized': 'You are not Authorized to change a super admin.'}, 400)
    else:
      return custom_response({'Unauthorized': 'You are not admin.'}, 400)


@user_api.route('/update', methods=['PUT'])
@Auth.auth_required
def update():
    req_data = request.get_json()
    data, error = user_schema.load(req_data, partial=True)
    if error:
        return custom_response(error, 400)
    user = UserModel.get_one_user(g.user.get('id'))
    user.update(data)
    ser_user = user_schema.dump(user).data
    return custom_response(ser_user, 200)


@user_api.route('/<int:user_id>', methods=['GET'])
def get_a_user(user_id):
    user = UserModel.get_one_user(user_id)
    if not user:
        return custom_response({'error': 'User not found.'}, 404)
    ser_user = user_schema.dump(user).data
    return custom_response(ser_user, 200)


@user_api.route('/delete', methods=['DELETE'])
@Auth.auth_required
def delete():
    user = UserModel.get_one_user(g.user.get('id'))
    if not user:
        return custom_response({'error': 'User not found.'}, 404)
    google.delete_user_google(str(g.user.get('id')))
    user.delete()
    return custom_response({'message': 'deleted'}, 204)


@user_api.route('/get_me', methods=['GET'])
@Auth.auth_required
def get_me():
    user = UserModel.get_one_user(g.user.get('id'))
    ser_user = user_schema.dump(user).data
    return custom_response(ser_user, 200)


@user_api.route('/login', methods=['POST'])
def login():
    req_data = request.get_json()
    data, error = user_schema.load(req_data, partial=True)
    if error:
        return custom_response(error, 400)
    if not data.get('email') or not data.get('password'):
        return custom_response({'error': 'You need email and password to sign in'}, 400)
    user = UserModel.get_user_by_email(data.get('email'))
    if not user:
        return custom_response({'error': 'invalid credentials'}, 400)
    if user_schema.dump(user).data.get('social_id') == 1:
        return custom_response({'error': 'invalid credentials'}, 400)
    if not user.check_hash(data.get('password')):
        return custom_response({'error': 'invalid credentials'}, 400)
    token = Auth.generate_token(user_schema.dump(user).data.get('id'))
    return custom_response(UserModel.info_user(user, token), 200)


@user_api.route('/google_login', methods=['POST'])
def google_login():
    google_auth = google.get_google_auth(token=request.get_json())
    resp = google_auth.get(google.USER_INFO)
    if resp.status_code == 200:
        user_data = resp.json()
        data = {
            'firstname': user_data['given_name'],
            'lastname': user_data['family_name'],
            'email': user_data['email'],
            'picture': user_data['picture'],
            'password': 'google_auth'
        }
        user_in_db = UserModel.get_user_by_email(data['email'])
        if user_in_db:
            token = Auth.generate_token(user_schema.dump(user_in_db).data.get('id'))
            return custom_response(UserModel.info_user(user_in_db, token), 200)
        user = UserModel(data, 1, "0000-1")
        user.save()
        profile = ProfileModel({}, user.id)
        profile.picture_profile(data.get('picture'), "empty")
        profile.save()
        NotifModel.init_by_user_id(user.id)
        token = Auth.generate_token(user_schema.dump(user).data.get('id'))
        return custom_response(UserModel.info_user(user, token), 200)
    return custom_response("Unauthorized, Could not fetch your information.", 400)


@user_api.route('/logout', methods=['DELETE'])
@Auth.auth_required
def logout():
    revoked_token = RevokedTokenModel(request.headers['api-token'])
    revoked_token.save()
    return custom_response({'message': 'Access token has been revoked.'}, 200)