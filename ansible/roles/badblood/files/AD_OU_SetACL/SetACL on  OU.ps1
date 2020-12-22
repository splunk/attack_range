 $drive = "ad"
 
#====================
#Get a reference to the RootDSE of the current domain
$schemaPath = (Get-ADRootDSE)
$schemaobjects = Get-ADObject -filter * -SearchBase $schemaPath.defaultNamingContext -Properties * 
#Get a reference to the current domain
$domain = Get-ADDomain
#============================
#Create a hashtable to store the GUID value of each schema class and attribute
$guidmap = @{}
Get-ADObject -SearchBase ($schemaPath.SchemaNamingContext) -LDAPFilter  `
"(schemaidguid=*)" -Properties lDAPDisplayName,schemaIDGUID | 
% {$guidmap[$_.lDAPDisplayName]=[System.GUID]$_.schemaIDGUID}
#this shows what guids belong to which extended security group
    $attributesecurityguid = @{}
    Get-ADObject -SearchBase ($schemaPath.SchemaNamingContext) -LDAPFilter  `
    "(&(schemaidguid=*)(attributeSecurityGUID=*))" -Properties lDAPDisplayName,attributesecurityguid | 
    % {$attributesecurityguid[$_.lDAPDisplayName]=([guid]$_.attributesecurityguid).guid}sadfsdgfsdgfsdgfsdgfsdgf
#Create a hashtable to store the GUID value of each extended right in the forest
$extendedrightsmap = @{}
Get-ADObject -SearchBase ($schemaPath.ConfigurationNamingContext) -LDAPFilter `
"(&(objectclass=controlAccessRight)(rightsguid=*))" -Properties displayName,rightsGuid | 
% {$extendedrightsmap[$_.displayName]=[System.GUID]$_.rightsGuid}


#============================


 #$schemaobjects| where objectGUID -like '05e3036d-aa7a-49a1-8baf-efaca4f53fa2'|select ldapdisplayname,objectguid
 #$schemaobjects| where ldapdisplayname -like 'gecos'|select ldapdisplayname,objectguid
 
 #attributes to grant permissions to
 $AttributestoLookup = @('attname1','gecos')

 #apply to what object type
 $SchemaobjectToLookup = "user"
 $inheritedobjectguid = $schemaobjects| where Name -like $schemaobjecttolookup|select ldapdisplayname,objectGUID

 #group to get access described by attribute and object type above
$group = Get-ADgroup 'ewas-admin'
$sid = new-object System.Security.Principal.SecurityIdentifier $group.SID


#Domain and OU at which to grant access

$ou = 'OU=TESTOUNAME,DC=testdomain,DC=edu'
$ou = Get-ADOrganizationalUnit $ou
$acl = Get-ACL ($ou)


$access = Get-Acl -Path "$drive`:\\$OU"
#$access.access
<#
#$acl.Access|where-object identityreference -eq $group.sid.value
#############################################################################
ActiveDirectoryRights : ExtendedRight
InheritanceType       : None
ObjectType            : 00299570-246d-11d0-a768-00aa006e0529
InheritedObjectType   : 00000000-0000-0000-0000-000000000000
ObjectFlags           : ObjectAceTypePresent
AccessControlType     : Allow
IdentityReference     : S-1-5-21-870243273-3545234401-3913197981-137845
IsInherited           : False
InheritanceFlags      : None
PropagationFlags      : None
#>

foreach ($attribute in $AttributestoLookup){
$objectGUID = (($schemaobjects| where Name -like $attribute).objectGUID).guid
# The following object specific ACE is to grant Group permission to change user password on all user objects under OU
$objectguid = new-object Guid  $objectGUID #objectType
$inheritedobjectguid = new-object Guid  ($inheritedobjectguid.objectguid).GUID #inheritedobjecttype 
#$identity = [System.Security.Principal.IdentityReference] $SID #identityreference group that gains access
$identity = $SID #identityreference group that gains access
$adRights = [System.DirectoryServices.ActiveDirectoryRights] "ReadProperty, WriteProperty" #ActiveDirectoryRights
$type = [System.Security.AccessControl.AccessControlType] "Allow" #AccessControlType
$inheritanceType = [System.DirectoryServices.ActiveDirectorySecurityInheritance] "Descendents" #InheritanceType

#$objAcl.AddAccessRule((New-Object System.DirectoryServices.ActiveDirectoryAccessRule $groupSID,"WriteProperty,ReadProperty","Allow",$guidmap["memberOf"],$inheritanceType,$guidmap["user"]))
#$ace = new-object System.DirectoryServices.ActiveDirectoryAccessRule $identity,$adRights,$type,$objectGuid,$inheritanceType,$inheritedobjectguid
$ace = new-object System.DirectoryServices.ActiveDirectoryAccessRule $identity,$adRights,$type,$guidmap[$attribute],$inheritanceType,$guidmap[$SchemaobjectToLookup]

$acl.AddAccessRule($ace)

Set-Acl -path (get-adobject $ou.DistinguishedName) -AclObject $acl 

}
