# gino-quart

![test](https://github.com/python-gino/gino-quart/workflows/test/badge.svg)

## Introduction

An extension for [GINO](https://github.com/python-gino/gino) to support [quart](https://gitlab.com/pgjones/quart) server.

## Usage

The common usage looks like this:

```python
from quart import Quart
from gino.ext.quart import Gino

app = Quart()
db = Gino(app, **kwargs)
```

## Configuration

GINO adds a `before_request`, `after_request` and `before_first_request` hook to the Quart app to setup and cleanup database according to
the configurations that passed in the `kwargs` parameter.

The config includes:

| Name                         | Description                                                                                                       | Default     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------- |
| `driver`                     | the database driver                                                                                               | `asyncpg`   |
| `host`                       | database server host                                                                                              | `localhost` |
| `port`                       | database server port                                                                                              | `5432`      |
| `user`                       | database server user                                                                                              | `postgres`  |
| `password`                   | database server password                                                                                          | empty       |
| `database`                   | database name                                                                                                     | `postgres`  |
| `dsn`                        | a SQLAlchemy database URL to create the engine, its existence will replace all previous connect arguments.        | N/A         |
| `retry_times`                | the retry times when database failed to connect                                                                   | `20`        |
| `retry_interval`             | the interval in **seconds** between each time of retry                                                            | `5`         |
| `pool_min_size`              | the initial number of connections of the db pool.                                                                 | N/A         |
| `pool_max_size`              | the maximum number of connections in the db pool.                                                                 | N/A         |
| `echo`                       | enable SQLAlchemy echo mode.                                                                                      | N/A         |
| `ssl`                        | SSL context passed to `asyncpg.connect`                                                                           | `None`      |
| `use_connection_for_request` | flag to set up lazy connection for requests.                                                                      | N/A         |
| `retry_limit`                | the number of retries to connect to the database on start up.                                                     | 1           |
| `retry_interval`             | seconds to wait between retries.                                                                                  | 1           |
| `kwargs`                     | other parameters passed to the specified dialects, like `asyncpg`. Unrecognized parameters will cause exceptions. | N/A         |

## Lazy Connection

If `use_connection_for_request` is set to be True, then a lazy connection is available
at `request['connection']`. By default, a database connection is borrowed on the first
query, shared in the same execution context, and returned to the pool on response.
If you need to release the connection early in the middle to do some long-running tasks,
you can simply do this:

```python
await request['connection'].release(permanent=False)
```

## Contributing

You're welcome to contribute to this project. It's really appreciated. Please [fork this project and create a pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork) to the [dev branch](https://github.com/python-gino/gino-quart/tree/dev).

- Dependency management is done via [poetry](https://python-poetry.org/)
- Pull request for new features _must_ include the appropriate tests integrated in `tests/test_gino_quart.py`
- You should format your code. Recommended is [black](https://black.readthedocs.io/en/stable/)

## Attribution

The license holder of this extension is [Tony Wang](https://github.com/python-gino/gino-quart/blob/master/LICENSE).

This project is an extension to [GINO](https://github.com/python-gino/gino) and part of the [python-gino community](https://github.com/python-gino).
