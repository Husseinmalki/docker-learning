from flask import Flask
import redis

app = Flask(__name__)
r = redis.Redis()


@app.route('/')
def welcome():
    return "Welcome to my Docker web application"

@app.route('/count')
def counter():
    r.INCR('count')
    return r.get('count')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)