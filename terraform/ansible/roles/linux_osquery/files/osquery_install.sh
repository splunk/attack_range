#!/bin/bash
export OSQUERY_KEY=1484120AC4E9F8A1A577AEEE97A80C63C9D8B80B
export OSQUERY_REPO="deb [arch=amd64] https://pkg.osquery.io/deb deb main"

# Download and add the GPG key
curl -sSL https://pkg.osquery.io/deb/pubkey.gpg | sudo apt-key add -

# Add the repository
echo "$OSQUERY_REPO" | sudo tee /etc/apt/sources.list.d/osquery.list

# Update and install
sudo apt-get update
sudo apt-get install -y osquery