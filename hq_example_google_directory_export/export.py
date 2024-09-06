import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from os import environ as env
from dotenv import load_dotenv
import sys
import paramiko
from paramiko import SSHClient
import os


# Utility to gather the list of groups
def iterate_groups(service, groups_domain, SLEEP_TIME):
    page_token = None
    # TODO: Set to 50
    max_results = 5
    try:
        while True:
            results = service.groups().list(
                domain=groups_domain,
                pageToken=page_token,
                maxResults=max_results
            ).execute()
            groups = results.get('groups', [])
            page_token = results.get('nextPageToken')

            for group in groups:
                yield group['email']

            if not page_token:
                break

            # Sleep to avoid rate limiting
            time.sleep(SLEEP_TIME)
    except Exception as e:
        print(f"An error occurred retrieving groups: {e}", file=sys.stderr)


# Utility to gather the list of members in a group
def iterate_group_members(service, group_email, SLEEP_TIME, FETCH_USER_NAMES=False):
    page_token = None
    # TODO: Set to 50
    max_results = 5
    try:
        while True:
            results = service.members().list(
                groupKey=group_email,
                includeDerivedMembership=True,
                pageToken=page_token,
                maxResults=max_results
            ).execute()
            members = results.get('members', [])
            page_token = results.get('nextPageToken')

            for member in members:
                # If the fetch of the user details fails, assume the user is allowed in the group.
                # This happens when a user is within a sub-group within the main group
                member_settings = member
                try:
                    # Delivery status is not in the list response.
                    # Fetch the user details for the group.
                    member_settings = service.members().get(
                        groupKey=group_email,
                        memberKey=member.get('email')
                    ).execute()
                except Exception as e:
                    print(f"WARN: Unable to fetch user settings: {e}", file=sys.stderr)

                # If this is a user, also fetch the user details
                # 'name': {'familyName': '', 'fullName': '', 'givenName': ''}
                if member.get('type') == 'USER' and FETCH_USER_NAMES:
                    try:
                        user = service.users().get(userKey=member.get('email')).execute()
                        member_settings['name'] = user.get('name')
                    except Exception as e:
                        print(f"WARN: Unable to fetch user name: {e}", file=sys.stderr)

                yield member_settings

                # Sleep to avoid rate limiting on member details
                time.sleep(SLEEP_TIME)

            if not page_token:
                break

            # Sleep to avoid rate limiting
            time.sleep(SLEEP_TIME)
    except Exception as e:
        print(f"An error occurred retrieving members: {e}", file=sys.stderr)


def write_user_row(member, users_csv):
    user_id = member.get('email')
    first_name = member.get('name', {}).get('givenName', user_id)
    last_name = member.get('name', {}).get('familyName', user_id)
    email = member.get('email')
    username = member.get('email')
    job_title = 'Not Available'

    users_csv.write(f"{user_id},{first_name},{last_name},{email},{username},{job_title}\n")


# Load env configuration or values from a .env file
load_dotenv()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = env['SERVICE_ACCOUNT_FILE']

# Define the required scopes
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group.member.readonly',
          'https://www.googleapis.com/auth/admin.directory.group.readonly',
          'https://www.googleapis.com/auth/admin.directory.user.readonly']

# Admin user to impersonate (domain-wide delegation)
ADMIN_USER = env['ADMIN_USER']
GROUPS_DOMAIN = env['GROUPS_DOMAIN']
SLEEP_TIME = 0
if 'SLEEP_TIME' in env:
    SLEEP_TIME = int(env['SLEEP_TIME'])
if 'FETCH_USER_NAMES' in env:
    FETCH_USER_NAMES = env['FETCH_USER_NAMES'].lower() == 'true'

# Create credentials using the service account file and scopes
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=ADMIN_USER)

BUILD_CSV_FILES = env.get('BUILD_CSV_FILES', 'False').lower() == 'true'
SHIP_CSV_FILES = env.get('SHIP_CSV_FILES', 'False').lower() == 'true'
DELETE_CSV_FILES = env.get('DELETE_CSV_FILES', 'False').lower() == 'true'

if not BUILD_CSV_FILES and not SHIP_CSV_FILES and not DELETE_CSV_FILES:
    print("No action specified. Exiting.")
    sys.exit(1)

USER_CSV_FILE = env.get('USER_CSV_FILE', 'users.csv')
USER_GROUPS_CSV_FILE = env.get('USER_GROUPS_CSV_FILE', 'user_groups.csv')

if BUILD_CSV_FILES:
    # Create a service object for the Groups Settings API
    service = build('admin', 'directory_v1', credentials=credentials)

    # Replace 'group@example.com' with the email address of your group
    group_emails = []
    if 'GROUP_EMAILS' in env and len(env['GROUP_EMAILS']) > 0:
        group_emails = env['GROUP_EMAILS'].split(',')
    else:
        group_emails = iterate_groups(service, GROUPS_DOMAIN, SLEEP_TIME)

    # Iterate over the groups and users emails, do not add users we've already processed
    users_included = set()

    with open(USER_CSV_FILE, 'w') as users_csv:
        # Write the header row
        users_csv.write('user_id,first_name,last_name,email,username,job_title\n')

        with open(USER_GROUPS_CSV_FILE, 'w') as groups_csv:
            # Write the header row
            groups_csv.write('group_name,user_id\n')

            for group_email in group_emails:
                print(f"Processing group: {group_email}")

                # Retrieve the group's members
                try:
                    members = iterate_group_members(service, group_email, SLEEP_TIME, FETCH_USER_NAMES)

                    # Filter members with delivery settings set to NONE or DISABLED
                    for member in members:
                        if not member.get('email'):
                            # Skip members without an email address
                            continue

                        if member.get('type') == 'GROUP':
                            # Skip groups, subgroups should be unrolled automatically
                            continue

                        if member.get('status') != 'ACTIVE':
                            # Skip inactive members
                            continue

                        if member.get('delivery_settings') in ['NONE', 'DISABLED']:
                            # Skip members with disabled delivery settings
                            continue
                    
                        # Write the user to the CSV file
                        if member.get('email') not in users_included:
                            write_user_row(member, users_csv)
                            users_included.add(member.get('email'))

                        # Write the user-group relationship to the CSV file
                        groups_csv.write(f"{group_email},{member.get('email')}\n")
        
                except Exception as e:
                    print(f"An error occurred processing group {group_email}: {e}", file=sys.stderr)
    print("CSV files generated.")

if SHIP_CSV_FILES:
    # Send the CSV files to the SFTP server
    
    # SFTP connection details
    hostname = 'sftp.workos.com'
    port = 22  # Default SFTP port

    # Create an SFTP session and upload the file
    try:
        # Create an SSH client instance
        client = SSHClient()

        # Automatically add the server's host key (for first-time connection)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        private_key_path = env['SFTP_PRIVATE_KEY_FILE']
        SFTP_USERNAME = env['SFTP_USERNAME']
        key = paramiko.RSAKey.from_private_key_file(private_key_path)

        # Connect to the SFTP server
        client.connect(hostname, port, username=SFTP_USERNAME, pkey=key)

        # Create an SFTP session
        sftp = client.open_sftp()

        # Upload the files
        sftp.put(USER_CSV_FILE, 'users.csv')
        sftp.put(USER_GROUPS_CSV_FILE, 'user_groups.csv')

        # Close the SFTP session and SSH client
        sftp.close()
        client.close()

        print("sFTP files shipped.")
    except Exception as e:
        print(f"An error occurred: {e}")

if DELETE_CSV_FILES:
    # Delete the CSV files
    os.remove(USER_CSV_FILE)
    os.remove(USER_GROUPS_CSV_FILE)
    print(f"Deleted {USER_CSV_FILE} and {USER_GROUPS_CSV_FILE}")