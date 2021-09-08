#!/bin/bash
rm -rf attack_data/*

# AWS ECR Container Scanning Findings High
mkdir attack_data/aws_ecr_1
wget -O attack_data/aws_ecr_1/aws_ecr_scanning_findings_events.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1204.003/aws_ecr_image_scanning/aws_ecr_scanning_findings_events.json
python attack_range.py replay -dn aws_ecr_1 --source current_timestamp --sourcetype aws:cloudtrail --index test --file_name aws_ecr_scanning_findings_events.json
sleep 10
python attack_range.py search --search "ESCU - AWS ECR Container Scanning Findings High - Rule" --earliest 2h

# AWS ECR Container Scanning Findings Medium
python attack_range.py search --search "ESCU - AWS ECR Container Scanning Findings Medium - Rule" --earliest 2h

# AWS ECR Container Upload Unknown User
mkdir attack_data/aws_ecr_2
wget -O attack_data/aws_ecr_2/aws_ecr_container_upload.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1204.003/aws_ecr_container_upload/aws_ecr_container_upload.json
python attack_range.py replay -dn aws_ecr_2 --source current_timestamp --sourcetype aws:cloudtrail --index test --file_name aws_ecr_container_upload.json
sleep 10
python attack_range.py search --search "ESCU - AWS ECR Container Upload Unknown User - Rule" --earliest 2h

# Circle CI Disable Security Job
mkdir attack_data/ci1
wget -O attack_data/ci1/circle_ci_disable_security_job.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1554/circle_ci_disable_security_job/circle_ci_disable_security_job.json
python attack_range.py replay -dn ci1 --source circleci --sourcetype circleci --index test --file_name circle_ci_disable_security_job.json
sleep 10
python attack_range.py search --search "ESCU - Circle CI Disable Security Job - Rule" --earliest 2h

# Circle CI Disable Security Step
mkdir attack_data/ci2
wget -O attack_data/ci2/circle_ci_disable_security_step.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1554/circle_ci_disable_security_step/circle_ci_disable_security_step.json
python attack_range.py replay -dn ci2 --source circleci --sourcetype circleci --index test --file_name circle_ci_disable_security_step.json
sleep 10
python attack_range.py search --search "ESCU - Circle CI Disable Security Step - Rule" --earliest 2h

# Github Commit Changes In Master
mkdir attack_data/github1
wget -O attack_data/github1/github_push_master.log https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1199/github_push_master/github_push_master.log
python attack_range.py replay -dn github1 --source current_timestamp --sourcetype aws:firehose:json --index test --file_name github_push_master.log
sleep 10
python attack_range.py search --search "ESCU - Github Commit Changes In Master - Rule" --earliest 2h

# GitHub Dependabot Alert
mkdir attack_data/github2
wget -O attack_data/github2/github_security_advisor_alert.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1195.001/github_security_advisor_alert/github_security_advisor_alert.json
python attack_range.py replay -dn github2 --source current_timestamp --sourcetype aws:firehose:json --index test --file_name github_security_advisor_alert.json
sleep 10
python attack_range.py search --search "ESCU - GitHub Dependabot Alert - Rule" --earliest 2h

# GitHub Pull Request from Unknown User
mkdir attack_data/github3
wget -O attack_data/github3/github_pull_request.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1195.001/github_pull_request/github_pull_request.json
python attack_range.py replay -dn github3 --source current_timestamp --sourcetype aws:firehose:json --index test --file_name github_pull_request.json
sleep 10
python attack_range.py search --search "ESCU - GitHub Pull Request from Unknown User - Rule" --earliest 2h

# Gsuite Drive Share In External Email
mkdir attack_data/gsuite1
wget -O attack_data/gsuite1/gdrive_share_external.log https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1567.002/gsuite_share_drive/gdrive_share_external.log
python attack_range.py replay -dn gsuite1 --source current_timestamp --sourcetype gsuite:drive:json --index test --file_name gdrive_share_external.log
sleep 10
python attack_range.py search --search "ESCU - Gsuite Drive Share In External Email - Rule" --earliest 2h

# Gsuite Suspicious Shared File Name
mkdir attack_data/gsuite2
wget -O attack_data/gsuite2/gdrive_susp_attach.log https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1566.001/gdrive_susp_file_share/gdrive_susp_attach.log
python attack_range.py replay -dn gsuite2 --source current_timestamp --sourcetype gsuite:drive:json --index test --file_name gdrive_susp_attach.log
sleep 10
python attack_range.py search --search "ESCU - Gsuite Suspicious Shared File Name - Rule" --earliest 2h

# Kubernetes Nginx Ingress LFI
mkdir attack_data/k8s1
wget -O attack_data/k8s1/kubernetes_nginx_lfi_attack.log https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1212/kubernetes_nginx_lfi_attack/kubernetes_nginx_lfi_attack.log
python attack_range.py replay -dn k8s1 --source current_timestamp --sourcetype kube:container:controller --index test --file_name kubernetes_nginx_lfi_attack.log
sleep 10
python attack_range.py search --search "ESCU - Kubernetes Nginx Ingress LFI - Rule" --earliest 2h

# Kubernetes Scanner Image Pulling
mkdir attack_data/k8s2
wget -O attack_data/k8s2/kubernetes_kube_hunter.json https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1526/kubernetes_kube_hunter/kubernetes_kube_hunter.json
python attack_range.py replay -dn k8s2 --source current_timestamp --sourcetype kube:objects:events --index test --file_name kubernetes_kube_hunter.json
sleep 10
python attack_range.py search --search "ESCU - Kubernetes Scanner Image Pulling - Rule" --earliest 2h

# Correlations
python attack_range.py search --search "ESCU - Correlation by User and Risk - Rule" --earliest 4h
sleep 10
python attack_range.py search --search "ESCU - Correlation by Repository and Risk - Rule" --earliest 4h