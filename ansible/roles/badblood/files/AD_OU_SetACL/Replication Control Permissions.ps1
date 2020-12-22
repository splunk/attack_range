##Replication Tasks - Tier 0 only - do not code in structure
Function ManageReplicationTopology($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Manage Replication Topology"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Manage Replication Topology on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Manage Replication Topology on the OU " + $objOU)
}


}

Function ReplicatingDirectoryChanges($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Replicating Directory Changes"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Replicate Directory Changes on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Replicate Directory Changes on the OU " + $objOU)
}


}

Function ReplicatingDirectoryChangesAll($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Replicating Directory Changes All"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Replicate Directory Changes (All) on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Replicate Directory Changes (All) on the OU " + $objOU)
}


}

Function ReplicatingDirectoryChangesInFilteredSet($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Replicating Directory Changes In Filtered Set"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Replicate Directory Changes (In Filtered Set) on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Replicate Directory Changes (In Filtered Set) on the OU " + $objOU)
}


}

Function ReplicationSynchronization($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Replication Synchronization"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " the permission Replication Synchronization on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " the permission Replication Synchronization on the OU " + $objOU)
}

}