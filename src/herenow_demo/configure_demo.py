import os
import glob
import re
from argparse import ArgumentParser
import tomlkit

# Initialize argument parser
parser = ArgumentParser(
    description="Update app's pyproject.toml with the backend wheel and provide Docker build command."
)
parser.add_argument(
    "--backend-dist-dir",
    required=True,
    type=str,
    help="Directory within the Docker container where backend wheels are located.",
)
parser.add_argument(
    "--app-dir",
    required=True,
    type=str,
    help="Directory within the Docker container where herenow_demo is located.",
)
args = parser.parse_args()


# Function to extract the version from the wheel filename
def extract_version_from_wheel(wheel_name):
    match = re.search(r"(\d+\.\d+\.\d+[a-z]\d+)", wheel_name)
    return match.group(1) if match else None


# Function to update the app's pyproject.toml with the backend wheel path
def update_app_pyproject_with_backend_wheel(app_dir, backend_wheel_path):
    app_toml_path = os.path.join(app_dir, "pyproject.toml")
    with open(app_toml_path, "r", encoding="utf-8") as f:
        data = tomlkit.parse(f.read())

    # Assuming that 'drop-backend' is the package name in pyproject.toml
    data["tool"]["poetry"]["dependencies"]["drop-backend"] = {
        "file": backend_wheel_path
    }

    # Write the updated pyproject.toml back to file
    with open(app_toml_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(data))


# Main function to process the build and update operations
def main():
    backend_wheel_files = glob.glob(
        os.path.join(args.backend_dist_dir, "drop_backend-*.whl")
    )
    if backend_wheel_files:
        # Take the first wheel file (assuming there's only one)
        backend_wheel_path = backend_wheel_files[0]
        backend_version = extract_version_from_wheel(backend_wheel_path)

        # Construct the relative path for the backend wheel
        # This assumes that the backend wheel will be copied to the same directory structure in the Docker context as on the host
        backend_wheel_path = os.path.join(
            args.backend_dist_dir, f"drop_backend-{backend_version}-py3-none-any.whl"
        )
        update_app_pyproject_with_backend_wheel(args.app_dir, backend_wheel_path)
        # Generate the Docker build command for the app (assuming this script is part of the Docker build process)
        print("Updated app's pyproject.toml with the backend wheel.")
    else:
        print("No backend wheel file found.")


if __name__ == "__main__":
    main()
