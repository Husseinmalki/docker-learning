This Docker challenge requires us to create a multi-container application which consists of a simple python flask web application and a Redis database.

Its requirements:
Flask Web Application:

A Flask app that has two routes:
/: Displays a welcome message.
/count: Increments and displays a visit count stored in Redis.
Redis Database:

Use Redis as a key-value store to keep track of the visit count.
Dockerize Both Services:

Create Dockerfiles for both the Flask app and Redis.
Use Docker Compose to manage the multi-container application.
