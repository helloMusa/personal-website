from app import app
from waitress import serve

if __name__ == "__main__":
    # app.run(use_reloader=False, debug=True)
    serve(app, host='127.0.0.1', port=5000)