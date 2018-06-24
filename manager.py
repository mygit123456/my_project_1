from flask import current_app
from flask_migrate import MigrateCommand, Migrate
from flask_script import Manager
from info import create_app, db
from info import models
from info.models import User

app = create_app("development")
manager = Manager(app)
Migrate(app, db)
manager.add_command("mysql", MigrateCommand)

@manager.option("-n", "--name", dest="name")
@manager.option("-p", "--password", dest="password")
def create_super_user(name, password):
    user = User()
    user.nick_name = name
    user.mobile = name
    user.is_admin = True
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()



if __name__ == '__main__':
    print(app.url_map)
    manager.run()