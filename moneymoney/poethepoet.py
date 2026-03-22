from sys import argv
from moneymoney.reusing.github import download_from_github
from os import system, environ

def reusing():
    """
        Actualiza directorio reusing
        poe reusing
        poe reusing --local
    """
    local=False
    if len(argv)==2 and argv[1]=="--local":
        local=True
        print("Update code in local without downloading was selected with --local")
    if local==False:
        download_from_github("turulomio", "reusingcode", "python/decorators.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/file_functions.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/github.py", "moneymoney/reusing")
        download_from_github("turulomio", "django_calories_tracker", "calories_tracker/tests/tests_helpers.py", "moneymoney/reusing")
        download_from_github("turulomio", "django_calories_tracker", "calories_tracker/tests/tests_dinamic_methods.py", "moneymoney/reusing")


def testserver_e2e():
    print("- Dropping test_xulpymoney database...")
    system("dropdb -U postgres -h 127.0.0.1 test_xulpymoney")
    print("- Launching python manage.py test_server with user 'test' and password 'test' and fixed token to allow e2e paralellism")
    environ["E2E_TESTING"]="1"
    system("python manage.py testserver moneymoney/fixtures/all.json moneymoney/fixtures/test_server.json --addrport 8004")

def docker():
    """
        Builds and optionally pushes the Docker image for the Django application.
        Usage:
        poe docker             # Builds and pushes to Docker Hub
        poe docker --local     # Builds locally only, without pushing
    """
    local_only = False
    # Check if the '--local' argument is present (argv[0] is 'poe', argv[1] is 'docker')
    if len(argv) > 2 and argv[2] == "--local":
        local_only = True
        print("Building Docker image locally only.")
    else:
        print("Building and pushing Docker image to Docker Hub.")

    docker_username = environ.get("DOCKER_USERNAME")
    if not docker_username:
        print("Error: DOCKER_USERNAME environment variable not set.")
        print("Please set it (e.g., export DOCKER_USERNAME=your_docker_username) or modify the script.")
        return

    image_name = f"{docker_username}/django_moneymoney:latest"
    dockerfile_path = "./Dockerfile"
    context_path = "."

    build_command = f"docker build -t {image_name} -f {dockerfile_path} {context_path}"
    print(f"Executing: {build_command}")
    if system(build_command) != 0:
        print("Docker build failed.")
        return

    if not local_only:
        push_command = f"docker push {image_name}"
        print(f"Executing: {push_command}")
        if system(push_command) != 0:
            print("Docker push failed.")
            return
        print(f"Successfully built and pushed {image_name} to Docker Hub.")
    else:
        print(f"Successfully built {image_name} locally.")
