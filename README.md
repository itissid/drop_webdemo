# What is this?
The project marries Consious Urban Exploration(it is also kind of a productization of being "Here In The Moment" and Travel) and the "*new*" AI for infra. Its a seed for an idea on how to explore our neighborhoods all the while being Aware and being Here. Here can be at home or anywhere
in your city.

Awareness and being conscious of this moment are two ideas are very close to my heart(Meditation is a key component of it). I also love to travel but one can also be a "traveller" within their city(One might say we all travel on the weekend) exploring big places like NYC.

I live in Hoboken, NJ so this is only content from there and intended to present a PoC.

# What it looks like?

> *Landing Page: Drop a pin within the area(no location permissions requested)*
![Entry Point](./docs/EntryPointSmall.jpg)

> *Next: The "Conscious Exploration" bits of the product:)*
![First Screen](./docs/FirstScreenSmall.jpg)

> *Also importantly: The use of modern AI: A pipeline to retrieve structured info from unstructured text and use RAG(embeddings and the like) to enrich and classify the  content... So it does not appear like a smorgasbord of information.*
![Second Screen](./docs/DetailsSmall.jpg)

The stack that uses AI and generates the DB(in Sqlite!) is [here](http://github.com/itissid/Drop-PoT)

# What this repo contains?
The front end which calls the backend([here](http://github.com/itissid/Drop-PoT) and all the opsy stuff to get it onto a cloud(Ongoing).


# Stuff specific to building the demo(Opsy)
Docs are a WIP so things may not work in the short term as expected
## Building and Distributing the Wheel.
There were a lot of package install errors(Oh debian linux how precise you are) and wrangling with the initial pyproject.toml dependencies 
that needed rust/c++ etc. Often there were errors and it took a fair bit of time building them from wheels/sdists, so I removed the deps that were not needed to build these packages, cutting down immensely on the size of the final installed binaries. This took a while...

Iteration Loop(`code=>build=>deploy`): 
1. Build the wheel of the `drop_backed` project. Update it in the `herenow_demo`. Both of these should be installable via pip.
> A thing to note is that `poetry build`'s wheels don't exclude any deps from the pyproject.toml as explained [here](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202), but we can use `extras` in poetry and set the optional=true on them so that later pip does not install them unless we ask.

2. Once tested(from local docker), the builds will be tagged. We can copy them from the containers and push to pypi.
3. Use a second docker container to install these builds and deploy!

## Docker 1(DockerfileBuild): Tests if the wheels can be built and installed using pip:
0. Write code, prune unwanted deps in drop_backend.
 -  Run build.py to copy the code for docker build to find in its context:
 ```
 python build.py --pot-source=local --demo-source=local --pot-dir=/Users/sid/workspace/drop/ --demo-dir=/Users/sid/workspace/herenow_demo/
 ```
 > This creates a sandbox where the code for both projects is copied and then in that sandbox bumps the major/minor/patch version in pyproject.toml in `drop_backend` example `x.y.`z becomes alpha `x.y.(z+1)-alpha`

2. run `docker build ...` like so:
```
docker build --target backend-builder \
--build-arg DROP_BACKEND_DIR=drop_PoT \
--build-arg HERENOW_DEMO_DIR=herenow_demo  \
-t backend-image -f DockerfileBuild /tmp/subdir
```

- 2.1. Log into docker: `docker run -p 8000:8000 -it --entrypoint /bin/bash herenow_demo`
- 2.2. Fire up the python interpreter and try `import drop_backend` and look around if everything is fine.

- 2.3. Succeed? No -> Go back to 1 and repeat.
>  The configure_demo.py script runs and fills in the name of the built wheel of drop_backend in the pyproject.toml of herenow_demo. This is needed because the wheel name is not trivial to know until the wheel is built.
- 2.5 Now run the remaining docker build command:
```
docker build --target app-builder \
--build-arg DROP_BACKEND_DIR=drop_PoT
--build-arg HERENOW_DEMO_DIR=herenow_demo  \
-t app-image -f DockerfileBuild
/tmp/subdir
```
This will create the wheel of herenow_demo and install it in the docker container.

- 2.4. Upload drop_backend to pypi add dependency to herenow_demo. Make a git commit but don't push yet.

3. Fix bugs and prune unwanted deps in herenow_demo. Run build.py. 
4. Again run docker build command as above.
5. Did docker build succeed? No -> Go back to 4 and repeat
6. Log into the docker container:
```
docker run -p 8000:8000 -it --entrypoint /bin/bash herenow_demo
```
7. Try running the adhoc gunicorn command like so for the final test:
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
1. Now use the tag from last step for both the projects.
>  Change the pyproject.toml for herenow_demo to use the tag for dependency of drop_backend.
3. Build and push both to pypi and git.
4. Make any changes to database necessary. 

## Docker 2(DockerfileDeploy): This will be the container that will host the app and the SQLite DB.
0. Build the DockerfileDeploy.
```
docker build \
  --build-arg SQLITE_DB_PATH="sqlite:////app/drop.db" \
  --build-arg RELOAD_WEBAPP="True" \
  --build-arg SECRET_KEY="somthingsupersecret-key" \
  --build-arg ORS_API_ENDPOINT="http://127.0.0.1:8080/ors/v2/directions/{profile}" \
  --build-arg ALLOWED_ORIGINS="http://127.0.0.1:8000,http://localhost:8000" \
  -t herenow_demo_deploy .

```
1. Run the container:
```
docker run -p 8000:8000 -d herenow_demo_deploy
```
2. Check on the browser one last time!
3. Now that both the deps are in the container, push to registry.

## Next(Deploy docker to cloud)
TODO

# Notes
While building the above i realized that I am actually doing a mini release strategy. Something that github or gitlab can probably help me
do, were this to ever become a product.





[1 Python poetry extras](https://github.com/python-poetry/poetry/issues/2567#issuecomment-1100038202)