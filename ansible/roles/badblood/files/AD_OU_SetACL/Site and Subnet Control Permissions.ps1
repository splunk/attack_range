##Site Tasks - Tier 0 only - do not code in structure
Function CreateSiteObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["site"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create Site Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create Site Objects on the OU " + $objOU)
}



}

Function DeleteSiteObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["site"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete Site Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete Site Objects on the OU " + $objOU)
}



}

Function ModifySiteProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["site"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify site properties on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify site properties on the OU " + $objOU)
}


}


##Subnet Tasks - Tier 0 only - do not code in structure
Function CreateSubnetObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["subnet"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create Subnet Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create Subnet Objects on the OU " + $objOU)
}



}

Function DeleteSubnetObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["subnet"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete Subnet Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete Subnet Objects on the OU " + $objOU)
}



}

Function ModifySubnetProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["subnet"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify subnet properties on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify subnet properties on the OU " + $objOU)
}


}

##SiteLink Tasks - Tier 0 only - do not code in structure
Function CreateSiteLinkObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["sitelink"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create SiteLink Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create SiteLink Objects on the OU " + $objOU)
}



}

Function DeleteSiteLinkObjects($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["sitelink"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete SiteLink Objects on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete SiteLink Objects on the OU " + $objOU)
}



}

Function ModifySiteLinkProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["sitelink"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify SiteLink properties on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify SiteLink properties on the OU " + $objOU)
}


}