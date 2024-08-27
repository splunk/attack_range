import os
import sys
import yaml
import shutil
import requests
import boto3
from git import Repo
from helpers.splunk_app import SplunkApp, SplunkAppSessionToken
from helpers.attack_range_apps import (
    ATTACK_RANGE_SPLUNKBASE_APPS,
    ATTACK_RANGE_LOCAL_APPS,
)

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Clone security_content repository
repo_url = "https://github.com/splunk/security_content.git"
repo_path = os.path.join(script_dir, "security_content")
if not os.path.exists(repo_path):
    Repo.clone_from(repo_url, repo_path)
else:
    repo = Repo(repo_path)
    repo.remotes.origin.pull()

# Read data source object yml files
data_sources_path = os.path.join(repo_path, "data_sources")
data_sources = []

for filename in os.listdir(data_sources_path):
    if filename.endswith(".yml"):
        with open(os.path.join(data_sources_path, filename), "r") as file:
            data_sources.append(yaml.safe_load(file))

# Add ATTACK_RANGE_SPLUNKBASE_APPS to data_sources
data_sources.extend([{"supported_TA": [app]} for app in ATTACK_RANGE_SPLUNKBASE_APPS])

# Create apps folder if it doesn't exist
apps_folder = os.path.join(script_dir, "apps")
os.makedirs(apps_folder, exist_ok=True)

# Create S3 client
s3_client = boto3.client("s3")
bucket_name = "attack-range-appbinaries"

# Create a list to store successfully uploaded app names
uploaded_apps = []

# Iterate over data sources and download Splunk apps
validated_TAs = []
processed_apps = set()

token = SplunkAppSessionToken.get_splunk_base_session_token()
print(f"Obtained Splunk Base session token: {token}")

for data_source in data_sources:
    if "supported_TA" in data_source:
        for supported_TA in data_source["supported_TA"]:
            ta_identifier = (supported_TA.get("name"), supported_TA.get("version"))
            if ta_identifier in validated_TAs:
                continue
            if supported_TA.get("url") is not None:
                validated_TAs.append(ta_identifier)
                uid = int(str(supported_TA["url"]).rstrip("/").split("/")[-1])
                if uid not in processed_apps:
                    try:
                        splunk_app = SplunkApp(app_uid=uid)

                        # Create the new filename based on the specified pattern
                        app_filename_base = splunk_app.app_title.lower().replace(
                            " ", "-"
                        )
                        version_without_dots = splunk_app.latest_version.replace(
                            ".", ""
                        )
                        app_filename = f"{app_filename_base}_{version_without_dots}.tgz"

                        s3_key = app_filename

                        # Check if file exists in S3 bucket
                        try:
                            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                            print(f"File {s3_key} already exists in S3 bucket.")
                            uploaded_apps.append(s3_key)
                        except:
                            # File doesn't exist in S3, download from Splunkbase and upload to S3
                            full_app_path = os.path.join(apps_folder, app_filename)

                            # Download the app with the session token
                            download_url = splunk_app.latest_version_download_url
                            headers = {"X-Auth-Token": token}
                            response = requests.get(download_url, headers=headers)
                            response.raise_for_status()

                            with open(full_app_path, "wb") as file:
                                file.write(response.content)

                            print(
                                f"Downloaded {splunk_app.app_title} to {full_app_path}"
                            )

                            # Upload to S3
                            s3_client.upload_file(full_app_path, bucket_name, s3_key)
                            print(f"Uploaded {s3_key} to S3 bucket {bucket_name}")
                            uploaded_apps.append(s3_key)

                            # Remove the local file after upload
                            os.remove(full_app_path)
                            print(f"Removed local file {full_app_path}")

                        processed_apps.add(uid)
                    except Exception as e:
                        print(f"Error processing Splunk App with UID {uid}: {str(e)}")
                        processed_apps.add(uid)

# Add ATTACK_RANGE_LOCAL_APPS to uploaded_apps
uploaded_apps.extend(ATTACK_RANGE_LOCAL_APPS)

# Sort uploaded_apps alphabetically
uploaded_apps.sort()

# Update the attack_range_default.yml file
config_file = os.path.join(script_dir, "..", "configs", "attack_range_default.yml")

# Read the entire file content
with open(config_file, "r") as file:
    content = file.read()

# Prepare the new splunk_apps section
new_apps_section = "  splunk_apps:\n"
for app in uploaded_apps:
    new_apps_section += f"    - {app}\n"
new_apps_section += "  # List of Splunk Apps to install on the Splunk Server"

# Define the pattern to search for
pattern_start = "  splunk_apps:"
pattern_end = "  # List of Splunk Apps to install on the Splunk Server"

# Find the start and end positions of the section to replace
start_pos = content.find(pattern_start)
end_pos = content.find(pattern_end, start_pos) + len(pattern_end)

# Replace the old section with the new one
updated_content = content[:start_pos] + new_apps_section + content[end_pos:]

# Write the updated content back to the file
with open(config_file, "w") as file:
    file.write(updated_content)

print(f"Updated {config_file} with new splunk_apps list.")

# Remove the security_content folder
shutil.rmtree(repo_path)

# Remove all files ending with .tgz under apps directory
apps_dir = os.path.join(script_dir, "apps")
for filename in os.listdir(apps_dir):
    if filename.endswith(".tgz"):
        file_path = os.path.join(apps_dir, filename)
        try:
            os.remove(file_path)
            print(f"Removed {file_path}")
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

print("Removed all .tgz files under apps directory.")
