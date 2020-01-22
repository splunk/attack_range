<powershell>
$admin = [adsi]("WinNT://./Administrator, user")
$admin.PSBase.Invoke("SetPassword", "I-l1ke-Attack-Range!")
Invoke-Expression ((New-Object System.Net.Webclient).DownloadString('https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1'))
</powershell>
