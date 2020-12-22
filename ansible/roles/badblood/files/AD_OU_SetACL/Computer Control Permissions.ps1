######################################################################################################################
# Computer object permissions
Function CreateComputerAccount($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["computer"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create Computer Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create Computer Accounts on the OU " + $objOU)
}




}

Function DeleteComputerAccount($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["computer"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete Computer Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete Computer Accounts on the OU " + $objOU)
}


}

Function RenameComputerAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["distinguishedName"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["cn"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["name"],$inheritanceType,$guidmap["computer"]))
try
{
    Set-Acl -AclObject $objAcl -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Rename Computer Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Rename Computer Accounts on the OU " + $objOU)
}



}

Function DisableComputerAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["userAccountControl"],$inheritanceType,$guidmap["computer"]))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Disable Computer Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Disable Computer Accounts on the OU " + $objOU)
}



}

Function EnableDisabledComputerAccount($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["userAccountControl"],$inheritanceType,$guidmap["computer"]))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Enable Disabled Computer Accounts on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Enable Disabled Computer Accounts on the OU " + $objOU)
}


}

Function ModifyComputerProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["computer"]))
try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Modify Computer Properties on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Modify Computer Properties on the OU " + $objOU)
}


}

Function ResetComputerAccount($objGroup, $objOU, $inheritanceType)
{

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objacl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Reset Password"],$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Reset Computer Passwords on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Reset Computer Passwords on the OU " + $objOU)
}

}

Function ModifyComputerGroupMembership($objGroup, $objOU, $inheritanceType)
{

$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["memberOf"],$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify the computer group membership on OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify the computer group membership on OU " + $objOU)
}




}

Function SetComputerSPN($objGroup, $objOU, $inheritanceType)
{

$error.Clear()



$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ReadProperty,WriteProperty","Allow",$guidmap["servicePrincipalName"],$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Set Computer SPN on OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Set Computer SPN on OU " + $objOU)
}

}

Function ReadComputerTPMBitLockerInfo($objGroup, $objOU, $inheritanceType)
{
$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ReadProperty","Allow",$guidmap["msTPM-OwnerInformation"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ReadProperty","Allow",$guidmap["msFVE-KeyPackage"],$inheritanceType,$guidmap["msFVE-RecoveryInformation"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ReadProperty","Allow",$guidmap["msFVE-RecoveryPassword"],$inheritanceType,$guidmap["msFVE-RecoveryInformation"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to read BitLocker and TPM Information on OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to read BitLocker and TPM Information on OU " + $objOU)
}

}

Function ReadComputerAdmPwd($objGroup, $objOU, $inheritanceType)
{
$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

# The schema must be extended for LAPS
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ReadProperty","Allow",$guidmap["ms-Mcs-AdmPwd"],$inheritanceType,$guidmap["computer"]))
#Added by JMN.  Need All Extended Rights on computer object to be able to Read LAPS password. LAPS password is Confidential attribute
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to read local administrator password on OU" + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to read local administrator password on OU " + $objOU)
}

}

Function ResetComputerAdmPwd($objGroup, $objOU, $inheritanceType)
{
$error.Clear()

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU

# The schema must be extended for LAPS
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["ms-Mcs-AdmPwdExpirationTime"],$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to reset local administrator password on OU" + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to reset local administrator password on OU " + $objOU)
}

}

Function DomainJoinComputers($objGroup, $objOU, $inheritanceType)
{
$error.Clear()

$rootdse = Get-ADRootDSE

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU   

$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild,DeleteChild","Allow",$guidmap["computer"],"All"))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Reset Password"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Account Restrictions"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Validated write to DNS host name"],$inheritanceType,$guidmap["computer"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"ExtendedRight","Allow",$extendedrightsmap["Validated write to service principal name"],$inheritanceType,$guidmap["computer"]))

try
{
    Set-Acl -AclObject $objAcl  -path $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to join computers to the domain in OU" + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to join computers to the domain in OU " + $objOU)
}

}