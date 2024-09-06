# Welcome
This is an example script to pull all users from a Google Directory account, pushing those users and groups to WorkOS via sFTP.

This example is provided as-is, as a template for anyone needing to interact with their Google group users.  It is intended to be adapted to the specific needs and situation of each client.

# Getting Started
All configuration options are outlined in `.env.template`.  These values can be set through environment variables or by copying `.env.template` to a file named `.env`.

This script makes API calls to the Google admin directory API.
The scopes needed by the `export.py` script are:
* 'https://www.googleapis.com/auth/admin.directory.group.member.readonly'
* 'https://www.googleapis.com/auth/admin.directory.group.readonly'
* 'https://www.googleapis.com/auth/admin.directory.user.readonly'

# To enable the Google API
To obtain a service account JSON file from Google Admin, follow these steps:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/):
* Open your web browser and go to the Google Cloud Console.
2. Create a New Project (if you don't have one already):
* Click on the project dropdown at the top of the page.
* Click on "New Project".
* Enter a project name and click "Create".
3. Enable the API:
* In the left-hand menu, go to "APls & Services" > "Library".
* Search for the `Admin SDK API`.
* Click on the `Admin SDK API` and then click "Enable".
4. Create Service Account:
* In the left-hand menu, go to "APls & Services" > "Credentials".
* Click on "Create Credentials" and select
"Service account".
* Fill in the service account details and click "Create".
5. Grant Roles to the Service Account:
* After creating the service account, you will be prompted to grant roles.
* Select the appropriate roles for your service account (e.g., "Owner", "Editor", or specific roles related to the API you are using).
6. Create Key:
* After creating the service account, click on the service account name to open its details.
* Go to the "Keys" tab.
* Click on "Add Key" > "Create new key".
* Select "JSON" and click "Create".
* A JSON file will be downloaded to your computer. This is your service account key file.
7. Delegate Domain-Wide Authority:
* If your application needs to access user data, you need to delegate domain-wide authority to the service account.
* In the [Google Admin Console](https://admin.google.com/ac/owl/domainwidedelegation), go to
"Security" > "API controls" > "Manage Domain Wide Delegation".
* Click "Add new" and enter the client ID of your service account and the scopes required (see above).

The credentials file downloaded in step 6 will be referenced by the `SERVICE_ACCOUNT_FILE` env variable.

# Running the `export.py` script
This script uses [poetry](https://python-poetry.org/) for dependency management.
All dependencies are managed in the `pyproject.toml` file.  See the file or run `poetry show` to list the project dependencies.

You can launch a shell with the complete python environment with `poetry shell` or, alternatively, you can run the export process
with `poetry run python hq_example_google_directory_export/export.py`