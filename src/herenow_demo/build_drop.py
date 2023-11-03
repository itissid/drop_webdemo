#!/usr/bin/env python3
from argparse import ArgumentParser
from configparser import ConfigParser
import os
import shutil
import fnmatch
import subprocess
import tomlkit
import semver

# Initialize argument parser
parser = ArgumentParser(
    description="Prepare and build Docker image for drop_PoT and herenow_demo projects."
)
parser.add_argument(
    "--pot-source",
    choices=["github", "local"],
    required=True,
    help="Source to fetch drop_PoT from: github or local.",
)
parser.add_argument(
    "--demo-source",
    choices=["github", "local"],
    required=True,
    help="Source to fetch herenow_demo from: github or local.",
)
parser.add_argument(
    "--pot-dir",
    required=True,
    type=str,
    help="Local directory of drop_PoT if source is local.",
)
parser.add_argument(
    "--demo-dir",
    required=True,
    type=str,
    help="Local directory of herenow_demo if source is local.",
)
parser.add_argument(
    "--pot-tag",
    type=str,
    help="Tagged version of drop_PoT to clone if source is github.",
)
parser.add_argument(
    "--demo-tag",
    type=str,
    help="Tagged version of herenow_demo to clone if source is github.",
)
parser.add_argument(
    "--update-backend-version",
    action="store_true",
    help="Update the patch version of the backend project to an alpha version before the build.",
    default=True,
)
parser.add_argument(
    "--bump-version",
    choices=["major", "minor", "patch"],
    default="patch",
    help="Part of the version to bump (major, minor, patch).",
)
print("Argument parser setup done.")


def run_poetry_commands(project_dir):
    # Run poetry check to validate the pyproject.toml file
    subprocess.run(["poetry", "check"], cwd=project_dir, check=True)

    # Run poetry update to update the dependencies and lock file
    subprocess.run(["poetry", "update"], cwd=project_dir, check=True)


def clone_or_copy_project_with_ignore(
    source, project_name, local_dir=None, git_tag=None, temp_dir=None
):
    def ignore_function(_, filenames):
        ignore_list = [
            ".idea",
            ".env",
            "venv",
            "env",
            "__pycache__",
            "*.py[cod]",
            "*.log",
            "*.swp",
            "*.swo",
            "*.tmp",
            "*.sql",
            "*.db",
            "*.ini" ".vscode",
            "*.code-workspace",
            "pyvenv.cfg",
            ".python-version",
            "**/.DS_Store",
            "dist",
            "tests/",
        ]

        return [
            filename
            for filename in filenames
            if any(fnmatch.fnmatch(filename, ignore) for ignore in ignore_list)
        ]

    dest_dir = os.path.join(temp_dir, project_name)

    if source == "github":
        git_url = f"https://github.com/itissid/{project_name}.git"

        subprocess.run(
            ["git", "clone", "--branch", git_tag, git_url, dest_dir], check=False
        )

    elif source == "local":
        # Copy from local directory

        shutil.copytree(local_dir, dest_dir, ignore=ignore_function)


# Function to update pyproject.toml to find the backend.
def update_pyproject_toml(demo_project_dir):
    toml_file = os.path.join(demo_project_dir, "pyproject.toml")

    config_parser = ConfigParser()

    config_parser.read(toml_file)

    # Update the dependency path for 'drop'

    config_parser.set(
        "tool.poetry.group.backend.dependencies",
        "drop",
        '{path = "/backend/", develop = true}',
    )

    # Write the changes back to pyproject.toml

    with open(toml_file, "w", encoding="utf-8") as f:
        config_parser.write(f)


def update_app_dependency(app_project_dir, backend_version):
    app_toml_file = os.path.join(app_project_dir, "pyproject.toml")

    # Construct the expected wheel filename
    backend_wheel_filename = f"drop_backend-{backend_version}-py3-none-any.whl"
    backend_wheel_path = f"/backend/dist/{backend_wheel_filename}"

    with open(app_toml_file, 'r', encoding='utf-8') as f:
        data = tomlkit.parse(f.read())

    # Update the dependency to point to the wheel file within the Docker container
    data['tool']['poetry']['dependencies']['drop-backend'] = {
        "file": backend_wheel_path
    }

    # Write the updated data back to pyproject.toml
    with open(app_toml_file, 'w', encoding='utf-8') as f:
        f.write(tomlkit.dumps(data))


def update_backend_version(backend_project_dir, version_part):
    toml_file = os.path.join(backend_project_dir, "pyproject.toml")

    with open(toml_file, "r", encoding="utf-8") as f:
        data = tomlkit.parse(f.read())

    # Get the current version
    version = data["tool"]["poetry"]["version"]

    # Bump the version
    if version_part == "major":
        new_version = semver.bump_major(version)
    elif version_part == "minor":
        new_version = semver.bump_minor(version)
    else:  # patch is the default
        new_version = semver.bump_patch(version)

    # Append the "-alpha" suffix
    new_version += "-alpha"

    # Update the version in the pyproject.toml data
    data["tool"]["poetry"]["version"] = new_version

    # Write the updated data back to pyproject.toml
    with open(toml_file, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(data))

    return new_version


def main():
    args = parser.parse_args()

    # Create a temporary directory
    if args.demo_dir:
        if not os.path.isdir(args.demo_dir):
            print(f"Error: {args.demo_dir} is not a valid directory.")
            exit(1)
    if args.pot_dir:
        if not os.path.isdir(args.pot_dir):
            print(f"Error: {args.pot_dir} is not a valid directory.")
            exit(1)
    #
    temp_dir = "/tmp/subdir"

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.makedirs(temp_dir, exist_ok=True)

    # Clone or copy drop_PoT project
    local_dropbackend_dir = "drop_PoT"
    if args.pot_source:
        clone_or_copy_project_with_ignore(
            args.pot_source, local_dropbackend_dir, args.pot_dir, args.pot_tag, temp_dir
        )
    else:
        raise ValueError("No backend source provided")

    # Clone or copy herenow_demo project
    local_drop_demo_dir = "herenow_demo"
    if args.demo_source:
        clone_or_copy_project_with_ignore(
            args.demo_source,
            local_drop_demo_dir,
            args.demo_dir,
            args.demo_tag,
            temp_dir,
        )
    else:
        raise ValueError("No demo source provided")

    backend_temp_dir = os.path.join(temp_dir, local_dropbackend_dir)
    run_poetry_commands(backend_temp_dir)

    if args.update_backend_version:
        backend_version = update_backend_version(
            backend_temp_dir, args.bump_version
        )
        backend_wheel_filename = f"drop_backend-{backend_version}-py3-none-any.whl"  # Construct the expected wheel filename
        backend_wheel_path = os.path.join(
            temp_dir, local_dropbackend_dir, "dist", backend_wheel_filename
        )
        update_app_dependency(
            os.path.join(temp_dir, local_drop_demo_dir), backend_wheel_path
        )

    # Update pyproject.toml in herenow_demo project

    # update_pyproject_toml(os.path.join(temp_dir, local_drop_demo_dir))

    # Execute Docker build command
    print("DONT forget to copy the database and the run the follwing")
    print(
        "To build docker image: fire the command",
        " ".join(
            [
                "docker",
                "build",
                "-t",
                "herenow_demo",
                "--build-arg",
                f"DROP_BACKEND_DIR={local_dropbackend_dir}",
                "--build-arg",
                f"DROP_DEMO_DIR={local_drop_demo_dir}",
                "-f",
                "Dockerfile",
                temp_dir,
            ]
        ),
    )
    # print('Building Docker image "herenow_demo" ...')
    # subprocess.run(
    #     [
    #         "docker",
    #         "build",
    #         "-t",
    #         "herenow_demo",
    #         "--no-cache",
    #         "--build-arg",
    #         f"DROP_BACKEND_DIR={local_dropbackend_dir}",
    #         "--build-arg",
    #         f"DROP_DEMO_DIR={local_drop_demo_dir}",
    #         "-f",
    #         "Dockerfile",
    #         "/tmp/subdir",
    #     ],
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE,
    #     check=True,
    # )
    # print('Done')
    # Wait for the process to finish


if __name__ == "__main__":
    main()
