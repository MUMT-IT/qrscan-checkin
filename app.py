from flask import Flask, render_template, request, jsonify
from datetime import datetime
from pytz import timezone
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


bangkok = timezone('Asia/Bangkok')

db = SQLAlchemy()
admin = Admin()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qrscan.db'
    app.config['SECRET_KEY'] = 'mumtfightcovid19'
    db.init_app(app)
    with app.app_context():
        db.create_all()
    admin.init_app(app)
    return app


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column('id', db.String(), primary_key=True)
    firstname = db.Column('firstname', db.String(), nullable=False)
    lastname = db.Column('lastname', db.String(), nullable=False)

    @property
    def fullname(self):
        return u'{} {}'.format(self.firstname, self.lastname)


class CheckIn(db.Model):
    __tablename__ = 'checkin_records'
    id = db.Column('id', db.Integer(), primary_key=True, autoincrement=True)
    checked_at = db.Column('checked_at', db.DateTime(timezone=True), nullable=False)
    user_id = db.Column('user_id', db.String(), db.ForeignKey('users.id'))
    user = db.relationship(User, backref=db.backref('checkin_records'))


app = create_app()

class UserAdminView(ModelView):
    form_columns = ('id', 'firstname', 'lastname')
    column_list = ('id', 'firstname', 'lastname')


admin.add_view(UserAdminView(User, db.session))
admin.add_view(ModelView(CheckIn, db.session))

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scan', methods=['POST'])
def read_cord():
    content = request.json
    user = User.query.filter_by(id=content['code']).first()
    if user:
        try:
            record = CheckIn()
            record.user = user
            record.checked_at = datetime.now(tz=bangkok)
            db.session.add(record)
            db.session.commit()
        except:
            return {'error': 'Failed to save to the database.'}
        else:
            return {'checked_in': datetime.now(tz=bangkok), 'code': content['code'], 'name': user.fullname}
    else:
        return {'error': 'Cannot find the user with that ID.'}


if __name__ == '__main__':
    app.run(debug=True)
