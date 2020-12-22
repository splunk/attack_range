Function AddRandomToGroups {
    
    [CmdletBinding()]
    
    param
    (
        [Parameter(Mandatory = $false,
            Position = 1,
            HelpMessage = 'Supply a result from get-addomain')]
            [Object[]]$Domain,
        [Parameter(Mandatory = $false,
            Position = 2,
            HelpMessage = 'Supply a result from get-aduser -filter *')]
            [Object[]]$UserList,
        [Parameter(Mandatory = $false,
            Position = 3,
            HelpMessage = 'Supply a result from Get-ADGroup -Filter { GroupCategory -eq "Security" -and GroupScope -eq "Global"  } -Properties isCriticalSystemObject')]
            [Object[]]$GroupList,
        [Parameter(Mandatory = $false,
            Position = 4,
            HelpMessage = 'Supply a result from Get-ADGroup -Filter { GroupScope -eq "domainlocal"  } -Properties isCriticalSystemObject')]
            [Object[]]$LocalGroupList,
        [Parameter(Mandatory = $false,
            Position = 5,
            HelpMessage = 'Supply a result from Get-ADComputer -f *')]
            [Object[]]$CompList
    )

    ##BEGIN STUFF
    if(!$PSBoundParameters.ContainsKey('Domain')){
        $dom = get-addomain
        $setDC = $dom.pdcemulator
        $dnsroot = $dom.dnsroot
        $dn = $dom.distinguishedname
    }
    else {
        $setDC = $Domain.pdcemulator
        $dnsroot = $Domain.dnsroot
    }
    if (!$PSBoundParameters.ContainsKey('UserList')){
        $allUsers = get-aduser -Filter *
    }else {
        $allUsers = $UserList
    }
    if (!$PSBoundParameters.ContainsKey('GroupList')){
        $allGroups = Get-ADGroup -Filter { GroupCategory -eq "Security" -and GroupScope -eq "Global"  } -Properties isCriticalSystemObject
    }else {
        $allGroups = $GroupList
    }
    if (!$PSBoundParameters.ContainsKey('LocalGroupList')){
        $allGroupsLocal = Get-ADGroup -Filter { GroupScope -eq "domainlocal"  } -Properties isCriticalSystemObject
    }else {
        $allGroupsLocal = $LocalGroupList
    }
    if (!$PSBoundParameters.ContainsKey('CompList')){
        $allcomps = Get-ADComputer -f *
    }else {
        $allcomps = $CompList
    }
    
cd ad:

<#Pick X number of random users#>
$UsersInGroupCount = [math]::Round($allusers.count * .8) #need to round to int. need to check this works
$GroupsInGroupCount = [math]::Round($allGroups.count * .2)
$CompsInGroupCount = [math]::Round($allcomps.count * .1)
<#
$groupsall = Get-ADGroup -Filter { GroupCategory -eq "Security" -and GroupScope -eq "Global"  } -Properties isCriticalSystemObject
PS \BadBlood> $groupsall.Count
1960
PS \BadBlood> $groupsall|where-object -Property iscriticalsystemobject -eq $true
#>
#get user list

$AddUserstoGroups = get-random -count $UsersInGroupCount -InputObject $allUsers
$allGroupsFiltered = $allGroups|where-object -Property iscriticalsystemobject -ne $true

#add a large number of users to a large number of non critical groups
Foreach ($user in $AddUserstoGroups){
    #get how many groups
    $num = 1..10|Get-Random
    $n = 0
    do{
        $randogroup = $allGroupsFiltered|Get-Random
        #add to group
        try{Add-ADGroupMember -Identity $randogroup -Members $user}
        catch{}
        $n++
    }while($n -le $num)
}

#add a few people to a small number of critical groups
$allGroupsCrit = $allGroups|where-object -Property iscriticalsystemobject -eq $true|Where-Object -Property name -ne "Domain Users" | Where-Object -Property name -ne "Domain Guests"
$allGroupsCrit|%{
    $num = 2..5|Get-Random
    
        try{Add-ADGroupMember -Identity $_ -Members (get-random -count $num -InputObject $allUsers)}
        catch{}
        
    
}

#add a few people to a small number of critical local groups
$allGroupsLocal|%{
    $num = 1..3|Get-Random
    
        try{Add-ADGroupMember -Identity $_ -Members (get-random -count $num -InputObject $allUsers)}
        catch{}
        
}

#$AddUserstoGroups = get-random -count (2..8|get-random) -InputObject $allUsers
#do nesting for all groups
#add a large number of users to a large number of non critical groups
#source is the input obj allGroupsFiltered, so i'm basically adding allgroupsfiltered to random non significant groups in AD.
#this is like adding domain admins to 'iis server 1 admins'  or 'pwd reset' groups

$AddGroupstoGroups = get-random -count $GroupsInGroupCount -InputObject $allGroupsFiltered

Foreach ($group in $AddGroupstoGroups){
    #get how many groups
    $num = 1..2|Get-Random
    $n = 0
    do{
        $randogroup = $allGroupsFiltered|Get-Random
        #add to group
        try{Add-ADGroupMember -Identity $randogroup -Members $group}
        catch{}
        $n++
    }while($n -le $num)
}
# add all critical groups to 2-5 other random groups


$allGroupsCrit|%{
    #get how many groups
    $num = 1..3|Get-Random
    $n = 0
    do{
        $randogroup = $allGroupsFiltered|Get-Random
        #add to group
        try{Add-ADGroupMember -Identity $randogroup -Members $_}
        catch{}
        $n++
    }while($n -le $num)
}


$addcompstoGroups = @()
$addcompstogroups = get-random -count $compsInGroupCount -InputObject $allcomps


Foreach ($comp in $addcompstogroups){
    #get how many groups
    $num = 1..5|Get-Random
    $n = 0
    do{
        $randogroup = $allGroupsFiltered|Get-Random
        #add to group
        try{Add-ADGroupMember -Identity $randogroup -Members $comp}
        catch{}
        $n++
    }while($n -le $num)
}



}

