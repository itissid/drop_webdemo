ADDITIONAL_ARGS="$@"
if [ -z "${ADDITIONAL_ARGS}" ]; then
    echo "Error: ADDITIONAL_ARGS is not set."
    exit 1
fi
BUILD_ARGS=""
while IFS= read -r line; do
    key=${line%%=*}
    value=${line#*=}
    BUILD_ARGS+=" --build-arg $key=$value"
done < .env.preprod

echo "docker build --target base -t pre-deploy-herenow-demo -f DockerfileDeploy $BUILD_ARGS ${ADDITIONAL_ARGS} ."

