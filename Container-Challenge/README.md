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

Things learnt:
1. When dealing with a bridge network, the containers ports have to be exposed past the private network otherwise you will not be able to access them.
This is done by using the -p command when you run a container specifiying the container port to the host machine port e.g 5000:5000
2.Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint container-challenge-web-3 (75745f08e58f1ae2b8e957cc9ce77f890950e822f75e45ad506e2e6a93bdad87): Bind for 0.0.0.0:5000 failed: port is already allocated
This error was due to the web service having its ports be specifically tied to 5000:5000 instead of just exposing the port 5000 for the nginx load balancer.