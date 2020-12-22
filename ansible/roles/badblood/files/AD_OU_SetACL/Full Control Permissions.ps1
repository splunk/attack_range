######################################################################################################################
# Full Control permissions
Function FullControl($objGroup, $objOU,$inheritanceType)
{


$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"GenericAll","Allow","00000000-0000-0000-0000-000000000000",$inheritanceType,"00000000-0000-0000-0000-000000000000"))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU 
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " Full Control permissions")
  
    
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " Full Control permissions on the OU " + $objOU)
}



}

Function FullControlUsers($objGroup, $objOU, $inheritanceType)
{


$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"GenericAll","Allow","00000000-0000-0000-0000-000000000000",$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU 
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " Full Control permissions over User Objects on the OU " + $objOU)
  
    
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " Full Control permissions over User Objects on the OU " + $objOU)
}



}

Function FullControlGroups($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"GenericAll","Allow","00000000-0000-0000-0000-000000000000",$inheritanceType,$guidmap["group"]))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU 
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " Full Control permissions over Group Objects on the OU " + $objOU)
  
    
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " Full Control permissions over Group Objects on the OU " + $objOU)
}



}

Function FullControlComputers($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"GenericAll","Allow","00000000-0000-0000-0000-000000000000",$inheritanceType,$guidmap["computer"]))
try
{
    Set-Acl -AclObject $objAcl  -path  $objOU 
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " Full Control permissions over Computer Objects on the OU " + $objOU)
  
    
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " Full Control permissions over Computer Objects on the OU " + $objOU)
}

}
