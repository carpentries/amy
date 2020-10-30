# Deploy AMY for PyData

 -  Export `AMY_ENABLE_PYDATA` environment variable.

```sh
    export AMY_ENABLE_PYDATA=true
```

 -  Export the username and password of a superuser of the conference site
    as environment variables.

```sh
    export AMY_PYDATA_USERNAME = "username"
    export AMY_PYDATA_PASSWORD = "password"
```

 -  Install fixtures from the `pydata/fixtures/` directory.

```sh
    python manage.py loaddata pydata/fixtures/*
```

 -  Ensure that all checks pass.

```sh
    python manage.py check
```
