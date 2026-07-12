from flask import Flask
from application.extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "appp"
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trek.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    login_manager.init_app(app)
    login_manager.login_view = "login"

    from application.app import init
    init(app)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)