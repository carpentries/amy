# Deploy AMY for PyData

 -  Add `pydata` to `INSTALLED_APPS`. Ensure that the `pydata` app is listed 
    before `workshops` app.

    ```py
    INSTALLED_APPS = (
        ...
        'pydata',
        'workshops',
        ...
    )
    ```

 -  Include `pydata.urls` in the `urlpatterns` of `amy.urls` before `workshops.url`.

    ```py
    urlpatterns = [
        ...
        url(r'^workshops/', include('pydata.urls')),
        url(r'^workshops/', include('workshops.urls')),
        ...
    ]
    ```

 -  Add the username and password of a superuser of the conference site to `amy/settings.py`.

    ```py
    PYDATA_USERNAME_SECRET = 'username'
    PYDATA_PASSWORD_SECRET = 'password'
    ```

    You can also fetch them from the environment variables.

    ```py
    PYDATA_USERNAME_SECRET = os.environ.get('PYDATA_USERNAME_SECRET')
    PYDATA_PASSWORD_SECRET = os.environ.get('PYDATA_PASSWORD_SECRET')
    ```

 -  Install fixtures from the `pydata/fixtures/` directory.

    ```sh
    python manage.py loaddata pydata/fixtures/*
    ```

 -  Ensure that all checks pass.

    ```sh
    python manage.py check
    ```
