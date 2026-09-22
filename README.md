# Container Challenge — Flask + Redis on Docker Compose

A multi-container web application: a Flask app that counts page visits in Redis, sitting behind an NGINX load balancer so the web tier can be scaled horizontally. Built as a hands-on Docker exercise, kept here with the problems it caused and how each one was diagnosed.

**Stack:** Python 3.13 (slim) · Flask · Redis · NGINX · Docker Compose

---

## Architecture

```
                    host :5000
                        |
                 +------v-------+
                 | loadbalancer |   nginx:latest
                 |    (nginx)   |   the only service that publishes a port
                 +------+-------+
                        | upstream flask_servers
        +---------------+---------------+
        |               |               |
   +----v----+     +----v----+     +----v----+
   |  web_1  |     |  web_2  |     |  web_3  |   built from ./Dockerfile
   +----+----+     +----+----+     +----+----+   expose 5000 (not published)
        |               |               |
        +---------------+---------------+
                        |
                 +------v-------+
                 | myRedisCache |   redis:latest
                 +------+-------+
                        |
                 +------v-------+
                 |  redis-data  |   named volume, survives restarts
                 +--------------+
```

Everything runs on Compose's default network. Containers reach each other by **service name** through Docker's embedded DNS — `myRedisCache` from the app, `web` from NGINX.

---

## Quick start

```bash
git clone https://github.com/Husseinmalki/docker-learning.git
cd docker-learning/Container-Challenge

# the app reads FLASK_PASS from the environment; compose reads it from .env
echo "FLASK_PASS=changeme" > .env

docker compose up -d
```

Then:

```bash
curl localhost:5000/                        # Welcome to my Docker web application
curl localhost:5000/count                   # 1
curl localhost:5000/count                   # 2
curl "localhost:5000/password?password=changeme"   # Correct Password!
```

Tear down, keeping the Redis data:

```bash
docker compose down
```

Tear down and wipe the volume too:

```bash
docker compose down -v
```

---

## Endpoints

| Route | Method | Behaviour |
|---|---|---|
| `/` | GET | Static welcome string |
| `/count` | GET | `INCR` the `count` key in Redis and return the new value |
| `/password` | GET | Compares `?password=` against `FLASK_PASS` with `hmac.compare_digest`; `200` or `401` |

`/password` uses a constant-time comparison rather than `==` so the check does not leak the expected value through response timing.

---

## Configuration

All configuration comes from the environment. Nothing is hardcoded in `app.py`.

| Variable | Set in | Purpose |
|---|---|---|
| `REDIS_HOST` | `docker-compose.yml` | Redis service name (`myRedisCache`) |
| `REDIS_PORT` | `docker-compose.yml` | `6379` |
| `FLASK_PASS` | `.env`, substituted into compose | Password for `/password` |

`.env` is git-ignored and docker-ignored. It is never committed and never enters the image.

**Precedence, verified with `docker compose config`:** an `environment:` block beats an `env_file:` entry for the same key, and `${VAR}` substitution reads from `.env` regardless. A variable that sits in `.env` and is never referenced does not reach the container at all.

---

## Scaling

```bash
docker compose up -d --scale web=3
docker compose ps
```

Three `web` replicas come up behind NGINX. No configuration change is needed to add them — `nginx.conf` points at a single upstream:

```nginx
upstream flask_servers {
    server web:5000;
}
```

Docker's DNS returns one A record per replica for `web`, so NGINX resolves the name to all three and round-robins between them.

**This only works because `web` does not publish a host port.** It uses `expose: "5000"`, which opens the port to the Compose network only. Three containers cannot all claim host port 5000, so the published port lives on the load balancer instead. That constraint is the reason the NGINX service exists.

---

## Project structure

```
Container-Challenge/
├── Dockerfile              # python:3.13-slim, single stage
├── app.py                  # Flask app: /, /count, /password
├── docker-compose.yml      # web + loadbalancer + myRedisCache, named volume
├── nginx/
│   └── nginx.conf          # upstream block + reverse proxy
├── .dockerignore           # keeps .env and friends out of the build context
├── .gitignore              # keeps .env out of git
└── README.md
```

---

## Problems hit, and how they were diagnosed

The point of the exercise. Each of these cost real time.

### 1. `AttributeError: 'Redis' object has no attribute 'INCR'`

`r.INCR('count')` → `r.incr('count')`.

redis-py maps Redis commands to **lowercase** Python methods. The uppercase name in the Redis documentation is the wire command, not the client method.

### 2. `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379. Connection refused.`

`redis.Redis()` defaults to `host="localhost"`, and inside a container `localhost` is *that container*. Redis was running in a different container on the same bridge network.

Fix: name the service. `redis.Redis(host="myRedisCache", port=6379, decode_responses=True)`, later moved to `os.environ`.

Diagnosing which half was broken came first:

```bash
docker exec myApp ping myRedisCache
```

Confirming the name resolved on the network ruled out DNS and pointed at the Python. The fix was one argument; proving *where* the fault was took the ping.

### 3. `port is already allocated` when scaling

The `web` service originally hard-bound `ports: "5000:5000"`. That is fine for one replica and impossible for three.

Fix: `expose: "5000"` on `web`, and move the published port onto the NGINX service. See [Scaling](#scaling).

### 4. Bridge network ports are not reachable from the host by default

Containers on a user-defined bridge network can talk to each other freely, but nothing on the host can reach them until a port is published (`-p 5000:5000`, or `ports:` in Compose). Exposing a port and publishing a port are different operations and the distinction is easy to miss.

### 5. Every code change reinstalled Flask and redis

The Dockerfile originally read:

```dockerfile
COPY . .
RUN pip install Flask redis
```

Docker caches each instruction as a layer, and a layer is invalid the moment anything above it changes. `COPY . .` changes whenever any project file changes, so editing one line of `app.py` invalidated the copy layer, which invalidated the install beneath it, which went back out to PyPI for two packages that had not changed in weeks.

Fix (commit `0753b12`) was to swap two lines:

```dockerfile
RUN pip install Flask redis
COPY . .
```

The `pip install` step measures at **3.5s** on this image, and that step is the only thing that differs between the two orderings. Rarely-changing things belong higher in the file.

### 6. `.gitignore` and `.dockerignore` are not the same list

`.gitignore` keeps `.env` out of the repository. It has no effect on `docker build`, which sends the whole directory as the build context — so with `COPY . .` in the Dockerfile, a git-ignored `.env` still lands inside the image.

Both files are needed, and `RUN rm .env` does not fix it: layers are immutable, so the file remains recoverable in the layer where it was added.

---

## Known gaps

Left deliberately, and recorded rather than hidden.

- **Dependencies are not pinned.** `RUN pip install Flask redis` resolves to whatever PyPI serves that day, so the build is not reproducible. Moving to a pinned `requirements.txt` with the split-COPY ordering is the next change.
- **The container runs as root.** `USER app` after a `useradd` is the fix and has not been made yet.
- **`depends_on` waits for start, not readiness.** Compose starts `myRedisCache` before `web`, but does not wait for Redis to accept connections. A `healthcheck` plus `condition: service_healthy` would close it. Without a healthcheck, there can be a window where the app starts before Redis is ready to accept connections.
- **Flask's development server is serving traffic.** Fine for an exercise, not for anything else. Gunicorn or uWSGI would be the real answer.
- **No CI.** The image is built by hand on a laptop.

---

## Related

- `../hello_flask/` — the single-container starting point this project grew out of.
