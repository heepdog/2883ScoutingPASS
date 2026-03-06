from flask import Flask
from flask import render_template, send_from_directory


app = Flask(__name__, static_url_path='/', static_folder='.')


@app.route("/")
def home():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    # Run the app with ad-hoc SSL context
    app.run(ssl_context='adhoc', port=4443, host='0.0.0.0')
