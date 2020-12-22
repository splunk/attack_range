#######
# Printer Tasks
Function CreatePrintQueue($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["printQueue"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Create Printer Queues on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Create Printer Queues on the OU " + $objOU)
}



}

Function DeletePrintQueue($objGroup, $objOU, $inheritanceType)
{

If($inheritanceType -eq "Descendents") { $inheritanceType="All"}
ElseIf($inheritanceType -eq "Children") { $inheritanceType="None"}

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"DeleteChild","Allow",$guidmap["printQueue"],$inheritanceType))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Delete Print Queues on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Delete Print Queues on the OU " + $objOU)
}

}

Function RenamePrintQueue($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["distinguishedName"],$inheritanceType,$guidmap["printQueue"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["cn"],$inheritanceType,$guidmap["printQueue"]))
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["name"],$inheritanceType,$guidmap["printQueue"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to Rename Print Queues on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to Rename Print Queues on the OU " + $objOU)
}




}

Function ModifyPrintQueueProperties($objGroup, $objOU, $inheritanceType)
{

$groupSID = New-Object System.Security.Principal.SecurityIdentifier $objGroup.SID
$objAcl = get-acl $objOU
$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$inheritanceType,$guidmap["printQueue"]))
try
{
    Set-Acl -AclObject $objAcl -path  $objOU
}
catch
{
    Write-Host -ForegroundColor Red ("ERROR: Unable to grant the group " + $objGroup.Name + " permissions to modify print queue properties on the OU " + $objOU)
}
If(!$error)
{
    Write-Host -ForegroundColor Green ("INFORMATION: Granted the group " + $objGroup.Name + " permissions to modify print queue properties on the OU " + $objOU)
}


}
