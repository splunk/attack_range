######
# GPO Tasks
Function LinkGPO($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["gplink"],$inheritanceType))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["gpoptions"],$inheritanceType))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to link group policies on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to link group policies on the OU " + $objOU)
}


}

Function GenerateRsopPlanning($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Generate resultant set of policy (Planning)"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " the permission Generate resultant set of policy (Planning) on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " the permission Generate resultant set of policy (Planning) on the OU " + $objOU)
}


}

Function GenerateRsopLogging($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Generate resultant set of policy (Logging)"],$inheritanceType,"00000000-0000-0000-0000-000000000000"))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " the permission Generate resultant set of policy (Logging) on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " the permission Generate resultant set of policy (Logging) on the OU " + $objOU)
}


}