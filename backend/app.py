"""Flask entry point for the applicant research demo foundation."""

from pathlib import Path

from flask import Flask, jsonify, request

if __package__:
    from . import config
    from .dataset import load_dataset
    from .storage import Storage
    from .experiment import Experiment, ExperimentError
else:
    import config
    from dataset import load_dataset
    from storage import Storage
    from experiment import Experiment, ExperimentError


def create_app(data_dir=None, db_path=None):
    frontend = Path(__file__).resolve().parent.parent / "frontend"
    app = Flask(__name__, static_folder=str(frontend), static_url_path="/static")
    app.config.from_object(config)
    # Validate once per application startup; invalid data prevents serving requests.
    app.extensions["dataset"] = load_dataset(data_dir)
    app.config['MAX_CONTENT_LENGTH'] = 400000  # Nine 5,000-character reasons, including JSON Unicode escapes.

    def experiment():
        if 'experiment' not in app.extensions:
            storage = Storage(db_path or Path(__file__).resolve().parent / 'outputs' / 'research.sqlite3')
            app.extensions['experiment'] = Experiment(app.extensions['dataset'], storage, settings=app.config)
        return app.extensions['experiment']

    def credential():
        header = request.headers.get('Authorization', '')
        return header[7:] if header.startswith('Bearer ') else ''

    @app.errorhandler(ExperimentError)
    def experiment_error(error):
        return jsonify(error=error.message), error.status

    @app.after_request
    def private_api(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/me')
    def me():
        return jsonify(experiment().me(credential()))

    @app.post('/api/action')
    def action():
        return jsonify(experiment().action(request.get_json(), credential()))

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", dataset_loaded=True)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
