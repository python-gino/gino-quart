import json
import os
import ssl

import gino
import pytest
from gino.ext.quart import Gino
from quart import Quart, jsonify, request, websocket
from quart.exceptions import NotFound

DB_ARGS = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", 5432),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASS", ""),
    database=os.getenv("DB_NAME", "postgres"),
)
PG_URL = "postgresql://{user}:{password}@{host}:{port}/{database}".format(**DB_ARGS)
pytestmark = pytest.mark.asyncio
_MAX_INACTIVE_CONNECTION_LIFETIME = 59.0


# noinspection PyShadowingNames
async def _app(config):
    app = Quart(__name__)
    app.config.update(config)
    app.config.update(
        {
            "DB_KWARGS": dict(
                max_inactive_connection_lifetime=_MAX_INACTIVE_CONNECTION_LIFETIME,
            ),
        }
    )

    db = Gino(app)

    class User(db.Model):
        __tablename__ = "gino_users"

        id = db.Column(db.BigInteger(), primary_key=True)
        nickname = db.Column(db.Unicode(), default="noname")

    @app.route("/")
    async def root():
        conn = await request.connection.get_raw_connection()
        # noinspection PyProtectedMember
        assert conn._holder._max_inactive_time == _MAX_INACTIVE_CONNECTION_LIFETIME
        return "Hello, world!"

    async def _get_user(ctx, uid: int, method: str) -> dict:
        q = User.query.where(User.id == uid)
        if method == "1":
            return (await q.gino.first_or_404()).to_dict()
        elif method == "2" and ctx:
            return (await ctx.connection.first_or_404(q)).to_dict()
        elif method == "3":
            return (await db.bind.first_or_404(q)).to_dict()
        elif method == "4":
            return (await db.first_or_404(q)).to_dict()
        else:
            return (await User.get_or_404(uid)).to_dict()

    @app.route("/users/<int:uid>")
    async def get_user(uid):
        method = request.args.get("method")
        return jsonify(await _get_user(request, uid, method))

    async def _add_user(ctx, nickname: str) -> dict:
        u = await User.create(nickname=nickname)
        await u.query.gino.first_or_404()
        await db.first_or_404(u.query)
        await db.bind.first_or_404(u.query)
        if ctx:
            await ctx.connection.first_or_404(u.query)
        return u.to_dict()

    @app.route("/users", methods=["POST"])
    async def add_user():
        return jsonify(await _add_user(request, (await request.form).get("name")))

    @app.websocket("/ws")
    async def ws():
        while True:
            data = json.loads(await websocket.receive())
            action = data.get("action")
            if action == "add":
                new_user = await _add_user(None, data.get("name"))
                await websocket.send(json.dumps(new_user))
            elif action == "get":
                try:
                    user = await _get_user(
                        None, int(data.get("id")), data.get("method")
                    )
                except NotFound:
                    await websocket.send(json.dumps({"error": "not found"}))
                else:
                    await websocket.send(json.dumps(user))
            else:
                await websocket.send(json.dumps({"error": "Invalid JSON"}))

    e = await gino.create_engine(PG_URL)
    try:
        try:
            await db.gino.create_all(e)
            yield app
        finally:
            await db.gino.drop_all(e)
    finally:
        await e.close()


@pytest.fixture
def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


@pytest.fixture
async def app():
    async for a in _app(
        {
            "DB_HOST": DB_ARGS["host"],
            "DB_PORT": DB_ARGS["port"],
            "DB_USER": DB_ARGS["user"],
            "DB_PASSWORD": DB_ARGS["password"],
            "DB_DATABASE": DB_ARGS["database"],
        }
    ):
        yield a


@pytest.fixture
async def app_ssl(ssl_ctx):
    async for a in _app(
        {
            "DB_HOST": DB_ARGS["host"],
            "DB_PORT": DB_ARGS["port"],
            "DB_USER": DB_ARGS["user"],
            "DB_PASSWORD": DB_ARGS["password"],
            "DB_DATABASE": DB_ARGS["database"],
            "DB_SSL": ssl_ctx,
        }
    ):
        yield a


@pytest.fixture
async def app_dsn():
    async for a in _app({"DB_DSN": PG_URL}):
        yield a


async def _test_index_returns_200(app):
    response = await app.test_client().get("/")
    assert response.status_code == 200
    assert await response.get_data(raw=False) == "Hello, world!"


async def test_index_returns_200(app):
    await _test_index_returns_200(app)


async def test_index_returns_200_dsn(app_dsn):
    await _test_index_returns_200(app_dsn)


async def _test(app):
    test_client = app.test_client()
    for method in "01234":
        response = await test_client.get("/users/1", query_string={"method": method})
        assert response.status_code == 404

    response = await test_client.post("/users", form=dict(name="fantix"))
    assert response.status_code == 200
    assert await response.get_json() == dict(id=1, nickname="fantix")

    for method in "01234":
        response = await test_client.get("/users/1", query_string={"method": method})
        assert response.status_code == 200
        assert await response.get_json() == dict(id=1, nickname="fantix")


async def test(app):
    await _test(app)


async def test_ssl(app_ssl):
    await _test(app_ssl)


async def test_dsn(app_dsn):
    await _test(app_dsn)


async def _websocket_request(ws, req: dict) -> dict:
    await ws.send(json.dumps(req).encode("utf-8"))
    return json.loads(await ws.receive())


async def _test_websocket(app):
    test_client = app.test_client()
    async with test_client.websocket("/ws") as ws:
        for method in "01234":
            response = await _websocket_request(
                ws, {"action": "get", "id": 1, "method": method}
            )
            assert response.get("error") == "not found"

        response = await _websocket_request(ws, {"action": "add", "name": "fantix"})
        assert response == dict(id=1, nickname="fantix")

        for method in "01234":
            response = await _websocket_request(
                ws, {"action": "get", "id": 1, "method": method}
            )
            assert response == dict(id=1, nickname="fantix")


async def test_ws(app):
    await _test_websocket(app)


async def test_ws_dsn(app_dsn):
    await _test_websocket(app_dsn)
