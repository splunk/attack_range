
$domain = $args[0]
$password = $args[2] | ConvertTo-SecureString -asPlainText -Force
$username = $args[1]
$credential = New-Object System.Management.Automation.PSCredential($username,$password)
Add-Computer -DomainName $domain -Credential $credential
