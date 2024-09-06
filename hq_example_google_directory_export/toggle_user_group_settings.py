from pprint import pprint
from google.oauth2 import service_account
from googleapiclient.discovery import build
from os import environ as env
from dotenv import load_dotenv

######################################################
# Utility to toggle the delivery status of a test user
# Change the member_email and group_key for your
# testing purposes
######################################################

# Load env configuration or values from a .env file
load_dotenv()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = env['SERVICE_ACCOUNT_FILE']

# Define the required scopes
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group.member']

# Admin user to impersonate (domain-wide delegation)
ADMIN_USER = env['ADMIN_USER']
GROUPS_DOMAIN = env['GROUPS_DOMAIN']

# Create credentials using the service account file and scopes
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=ADMIN_USER)

# Create a service object for the Groups Settings API
service = build('admin', 'directory_v1', credentials=credentials)

# Define the member's email address and group key
member_email = 'dave.cumberland@axioshq.com'
group_key = 'eevee@axioshq.com'

# Get the member's current delivery settings
member_settings = service.members().get(groupKey=group_key, 
                                        memberKey=member_email).execute()

pprint(member_settings)

# Toggle the delivery_setting value
if member_settings['delivery_settings'] == 'ALL_MAIL':
    new_delivery_setting = 'NONE'
else:
    new_delivery_setting = 'ALL_MAIL'

print(f"Updating {member_email} to {new_delivery_setting}")

# Update the member's delivery settings
service.members().update(
    groupKey=group_key,
    memberKey=member_email,
    body={'delivery_settings': new_delivery_setting}
).execute()
