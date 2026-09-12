from flask import Flask, request
import redis
import os, hmac

app = Flask(__name__)
r = redis.Redis(host=os.environ["REDIS_HOST"], port=os.environ["REDIS_PORT"], decode_responses=True)


@app.route('/')
def welcome():
    return "Welcome to my Docker web application"

@app.route('/count')
def counter():
    r.incr('count')
    return r.get('count')

@app.route('/password')
def password():
    guess = request.args.get("password", "")
    expected = os.environ["FLASK_PASS"]
    if hmac.compare_digest(guess, expected):
        return "Correct Password!"
    return "Incorrect Password", 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)