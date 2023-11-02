# drop_webdemo
Demo of Approximate Retrieval capability of LLMs appplied to build a product for Mindful Exploration of Urban Events.

# building and the dist process
There were a lot of errors and wrangling with the initial pyproject.toml dep packages
that needed rust/c++ etc. Often there were errors, so I removed the deps that were not needed to build these packages, cutting down immensely on the size of the final installed binaries. This is not testable on my non OSX machine.

Idea #1. Build the wheel of the drop_backed project. Then use it to test the drop_webdemo. Both of these should be installable via pip (and hopefully via poetry when its added to the package list). 
A thing to note is that poetry build runs wheels don't exclude any deps from the pyproject.toml as explained here[1](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202) but we can use `extras` in poetry and set the optional=true on them so that later pip does not install them unless we ask.

Here is how I iterated to build the docker images.

## Docker 1(DockerfileBuild): Tests if the wheels can be built and installed using pip:
0. Write code, prune unwanted deps in drop_backend.
> NOTE: You want to change the dependency of pyproject.toml in herenow_demo to use the local drop_backend.
 -  Run build.py to copy the code for docker build to find in its context:
 ```
 python build.py --pot-source=local --demo-source=local --pot-dir=/Users/sid/workspace/drop/ --demo-dir=/Users/sid/workspace/herenow_demo/
 ```
1. Change the dependency of drop_backend.
2. run `docker build ...` like so:
```
    docker build -t drop_webdemo \
    --build-arg DROP_BACKEND_DIR=drop_PoT \
    --build-arg HERENOW_DEMO_DIR=herenow_demo \
    -f DockerfileBuild /tmp/subdir
```

- 2.1. docker run -it --entrypoint /bin/bash drop_webdemo
- 2.2. Fire up the python interpreter and try `import drop_backend`.
``
- 2.3. Succeed? No -> Go back to 1 and repeat
- 2.4. upload drop_backend to git and pypi add dependency to drop_webdemo

3. Fix bugs and prune unwanted deps in drop_webdemo. Run build.py. 
4. Again run docker build command as above.
5. Did docker build succeed? No -> Go back to 4 and repeat
6. Log into the docker container:
```
docker run -p 8000:8000 -it --entrypoint /bin/bash drop_webdemo
```
6. Try running the adhoc gunicorn command like so for the final test:
```
gunicorn herenow_demo.main:app --bind 0.0.0.0:8000 --workers 1 \
--worker-class uvicorn.workers.UvicornWorker \
-e SQLITE_DB_PATH='sqlite:////app/drop.db' \
-e RELOAD_WEBAPP=True \
-e SECRET_KEY='supersecret-key' \
-e ORS_API_ENDPOINT='http://127.0.0.1:8080/ors/v2/directions/{profile}' \
-e ALLOWED_ORIGINS='http://127.0.0.1:8000,http://localhost:8000'
```

## Check in the tags, preprep for docker build
1. Now tag and push drop_backend.
2. Change the pyproject.toml for drop_webdemo to use the tag for dependency of drop_backend.
3. Tag and push drop_webdemo.
4. Make any changes to database. 

## Docker 2(DockerfileDeploy): This will be the container that will host the app.
0. Build the DockerfileDeploy.
```
docker build \
  --build-arg SQLITE_DB_PATH="sqlite:////app/drop.db" \
  --build-arg RELOAD_WEBAPP="True" \
  --build-arg SECRET_KEY="somthingsupersecret-key" \
  --build-arg ORS_API_ENDPOINT="http://127.0.0.1:8080/ors/v2/directions/{profile}" \
  --build-arg ALLOWED_ORIGINS="http://127.0.0.1:8000,http://localhost:8000" \
  -t drop_webdemo_deploy .

```
1. Check on the browser one last time!










[1](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202)