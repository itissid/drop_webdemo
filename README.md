# drop_webdemo
Demo of Approximate Retrieval capability of LLMs appplied to build a product for Mindful Exploration of Urban Events.

# building and the dist process
There were a lot of errors and wrangling with the initial pyproject.toml dep packages
that needed rust/c++ etc. Often there were errors, so I removed the deps that were not needed to build these packages, cutting down immensely on the size of the final installed binaries. This is not testable on my non OSX machine.

Idea #1. Build the wheel of the drop_backed project. Then use it to test the drop_webdemo. Both of these should be installable via pip (and hopefully via poetry when its added to the package list). 
A thing to note is that poetry build runs wheels don't exclude any deps from the pyproject.toml as explained here[1](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202) but we can use `extras` in poetry and set the optional=true on them so that later pip does not install them unless we ask.

Here is how I iterated to build the docker images.

## Docker1(DockerfileBuild): Tests if the wheels can be built and installed using pip:
0. fix deps in drop_backend. Run build.py.
1. COPY drop_backend/src to docker 
2. RUN poetry build 
3. `docker build ...`` Log into docker container and 
3.1 docker run -it --entrypoint /bin/bash drop_webdemo
3.2. poetry install
3.3. Succeed? No -> Go back to 1 and repeat
3.4. upload drop_backend to git and pypi add dependency to drop_webdemo
4. fix deps in drop_webdemo. Run build.py. 
5.  COPY drop_demo/src to docker 
6.  RUN poetry build
7. Success? No -> Go back to 4 and repeat

## Check in the tags, preprep for docker build
1. Now tag and push drop_backend.
2. Change the pyproject.toml for drop_webdemo to use the tag for dependency of drop_backend.
3. Tag and push drop_webdemo.
4. Make any changes to database. 

## Docker 2(DockerfileDeploy): This will be the container that will host the app.
0. Build the DockerfileDeploy.
1. Check on the browser.










[1](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202)