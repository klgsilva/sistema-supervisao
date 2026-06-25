import os

from flask import Flask

from app.extensions import db, login_manager, migrate


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.auth.routes import bp as auth_bp
    from app.main.routes import bp as main_bp
    from app.admin.routes import bp as admin_bp
    from app.visitas.routes import bp as visitas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(visitas_bp)

    @app.template_filter("brl")
    def brl(value):
        if value is None:
            value = 0
        texto = f"{float(value):,.2f}"
        return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return app
