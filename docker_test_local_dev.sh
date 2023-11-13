BUILD_ARGS=""
while IFS= read -r line; do
    key=${line%%=*}
    value=${line#*=}
    BUILD_ARGS+=" --build-arg $key=$value"
done < .env.local

echo "docker build --target app-tester -t local-herenow-demo-test -f DockerfileBuild $BUILD_ARGS  --build-arg DROP_BACKEND_DIR=drop_PoT  --build-arg HERENOW_DEMO_DIR=herenow_demo /tmp/subdir"

