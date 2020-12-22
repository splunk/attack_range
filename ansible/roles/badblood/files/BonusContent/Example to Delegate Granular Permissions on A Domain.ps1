Import-module activedirectory
cd ad:
#======================================================================
#Variables to set
$objgroup = get-adgroup 'Help Desk' #where $objgroup is the group you wan to grant access to
$objou = get-adorganizationalunit 'OU=Tier 2,DC=secframe,DC=com' #where this is the DN of the OU you want to apply the permissions onto.  You can use a group or user here too.
$inheritanceType = 'Descendents'  #because you want to do it to all descendant objects
#======================================================================

#=============================================
#import ACL function files
function Get-ScriptDirectory {
    Split-Path -Parent $PSCommandPath
}
$scriptPath = Get-ScriptDirectory
#$adplatformsourcedir = split-path -Path $scriptPath -Parent
$adplatformsourcedir = "c:\badblood" #if my scripts and AD_OU_SetACL scripts are in the c:\badblood folder, this will work.  point to the proper parent folder


#=============================================
#import ACL function files
$ACLScriptspath = $adplatformsourcedir + "\AD_OU_SetACL"

$files = Get-ChildItem $ACLScriptspath -Name "*permissions.ps1"
    foreach ($file in $files){
    .($aclscriptspath + "\"+$file)
    }
#end import
#=============================================
        #GUIDMAP is needed for the ACL scripts to run 
        #example portion of the acl script: $objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"CreateChild","Allow",$guidmap["computer"],$inheritanceType))
        #notice the guidmap in the above line 
        #Get a reference to the RootDSE of the current domain
        $schemaPath = (Get-ADRootDSE)
        #$schemaobjects = Get-ADObject -filter * -SearchBase $schemaPath.defaultNamingContext -Properties * 
        #Get a reference to the current domain
        $domain = Get-ADDomain
        #============================
        #Create a hashtable to store the GUID value of each schema class and attribute
        $guidmap = @{}
        Get-ADObject -SearchBase ($schemaPath.SchemaNamingContext) -LDAPFilter  `
        "(schemaidguid=*)" -Properties lDAPDisplayName,schemaIDGUID | 
        % {$guidmap[$_.lDAPDisplayName]=[System.GUID]$_.schemaIDGUID}

        #Create a hashtable to store the GUID value of each extended right in the forest
        $extendedrightsmap = @{}
        Get-ADObject -SearchBase ($schemaPath.ConfigurationNamingContext) -LDAPFilter `
        "(&(objectclass=controlAccessRight)(rightsguid=*))" -Properties displayName,rightsGuid | 
        % {$extendedrightsmap[$_.displayName]=[System.GUID]$_.rightsGuid}

FullControlUsers -objGroup $objgroup -objOU $objou -inheritanceType $inheritanceType
DomainJoinComputers -objGroup $objgroup -objOU $objou -inheritanceType $inheritanceType
DeleteComputerAccount -objGroup $objgroup -objOU $objou -inheritanceType $inheritanceType

#this script delegates permissions to allow the Help Desk Group onto the OU Tier2:
## FC to users
## domain join to computers 
## delete computers 
