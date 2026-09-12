from flask import Flask
import redis
import os

app = Flask(__name__)
r = redis.Redis(host=os.environ("REDIS_HOST"), port=os.environ("REDIS_PORT"), decode_responses=True)


@app.route('/')
def welcome():
    return "Welcome to my Docker web application"

@app.route('/count')
def counter():
    r.incr('count')
    return r.get('count')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)