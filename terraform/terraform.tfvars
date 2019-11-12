# AWS Keypair name is REQUIRED
key_name = ""
aws_region = "us-west-2"
ip_whitelist = ["0.0.0.0/0"]
win_username = "Administrator"
win_password = "myTempPassword123"

# path to the private key that belongs to the key_name in AWS
# we need this for ansible to build the machines 
private_key_path = ""~/.ssh/id_rsa"
