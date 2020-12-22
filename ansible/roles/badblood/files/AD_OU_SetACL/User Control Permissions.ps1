Function CreateUserAccount($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["user"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create User Accounts on the OU " + $objOU)
}


}

Function DeleteUserAccount($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["user"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete User Accounts on the OU " + $objOU)
}


}

Function RenameUserAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["distinguishedName"],$inheritanceType,$guidmap["user"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["cn"],$inheritanceType,$guidmap["user"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["name"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Rename User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Rename User Accounts on the OU " + $objOU)
}



}

Function DisableUserAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["userAccountControl"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Disable User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Disable User Accounts on the OU " + $objOU)
}



}

Function UnlockUserAccount($objGroup, $objOU, $inheritanceType)
{


$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["lockoutTime"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Unlock User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Unlock User Accounts on the OU " + $objOU)
}


}

Function EnableDisabledUserAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["userAccountControl"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Enable Disabled User Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Enable Disabled User Accounts on the OU " + $objOU)
}


}

Function ResetUserPasswords($objGroup, $objOU, $inheritanceType)
{


$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Reset Password"],$inheritanceType,$guidmap["user"]))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU -ErrorAction Stop
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Reset User Passwords on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Reset User Passwords on the OU " + $objOU)
}


}

Function ForcePasswordChangeAtLogon($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["pwdLastSet"],$inheritanceType,$guidmap["user"]))

try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Force Password Change at Logon on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Force Password Change at Logon on the OU " + $objOU)
}

}

Function ModifyUserGroupMembership($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["memberOf"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify a users group membership on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify a users group membership on the OU " + $objOU)
}

}

Function ModifyUserProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Modify User Properties on " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Modify User Properties on " + $objOU)
}


}

Function DenyModifyLogonScript($objGroup,$objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Deny",$guidmap["scriptPath"],$inheritanceType,$guidmap["user"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " deny permissions to Modify User Logon Script on " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " deny permissions to Modify User Logon Script on " + $objOU)
}


}

Function DenySetUserSPN($objGroup, $objOU, $inheritanceType)
{

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Deny",$guidmap["servicePrincipalName"],$inheritanceType,$guidmap["user"]))


try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " deny permissions to Create User SPNs on OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " deny permissions to Create User SPNs on OU " + $objOU)
}

}