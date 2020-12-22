#import config file of group types to create
Import-Module ActiveDirectory
function Get-ScriptDirectory {
    Split-Path -Parent $PSCommandPath
}
$scriptPath = Get-ScriptDirectory
$adplatformsourcedir = split-path -Path $scriptPath -Parent
$permissionset = .($adplatformsourcedir + "\AD_Group_CreateAdminGroups\AD Permissions for Group Granular Access.ps1")
#=====================================
#3 letter affiliate codes here
$3LetterCodeCSV = $adplatformsourcedir + '\AD_OU_CreateStructure\3lettercodes.csv'


#=============================================
#import ACL function files
$ACLScriptspath = $adplatformsourcedir + "\AD_OU_SetACL"

$files = Get-ChildItem $ACLScriptspath -Name "*permissions.ps1"
    foreach ($file in $files){
    .($aclscriptspath + "\"+$file)
    }
#=============================================
$dn = (Get-ADDomain).distinguishedname
#ADMIN Group Locations
#=============================================
#Tier 1
$Tier1GroupLocation = "OU=T1-Permissions,OU=Tier 1,OU=Admin" + ","+ $dn
#Tier 2
$Tier2GroupLocation = "OU=T2-Permissions,OU=Tier 2,OU=Admin" + "," + $dn
cd ad:
$dc = (get-addomain).PDCEmulator
#=============================================
       
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

        #Create a hashtable to store the GUID value of each extended right in the forest
        $extendedrightsmap = @{}
        Get-ADObject -SearchBase ($schemaPath.ConfigurationNamingContext) -LDAPFilter `
        "(&(objectclass=controlAccessRight)(rightsguid=*))" -Properties displayName,rightsGuid | 
        % {$extendedrightsmap[$_.displayName]=[System.GUID]$_.rightsGuid}





        #split csv lists into separate csvs because of the different OU structure
        $csvlist = @()
        $csvlist = import-csv $3LetterCodeCSV

#=============================================
#Permission set to OU names
#The function names in the formulas that grant acl permissions do not match our OU naming structure
$PermissionsToOUMapping = @{}
$PermissionsToOUMapping.Add('User','ServiceAccounts')
$PermissionsToOUMapping.Add('Computer','Devices')
$PermissionsToOUMapping.Add('Group','Groups')
$PermissionsToOUMapping.Add('OU','OU') #this mapping doesnt entirely matter since on line 94 OU permissions are applied directly to the OU containing the affiliate code
$PermissionsToOUMapping.Add('Printer', 'Devices')
#=============================================
#BEGIN MAKING GROUPS AND SETTING ACLS
$CSVCount = $csvlist.count
$x = 1
foreach ($3lettercode in $csvlist){
    Write-Progress -Activity "Deploying OU Structure" -Status "Affiliate Permissions Set Deploy Status:" -PercentComplete ($x/$CSVCount*100)
$code = $3lettercode.name
$toplevelTier1OUDN = 'OU=Tier 1,' + $dn
$toplevelTier2OUDN = 'OU=Tier 2,' + $dn
    foreach ($permission in $permissionset){
        if ($permission.APPLY -eq 'TRUE'){
        $t1groupname = ($code+ "_T1_" +($permission.FunctionSet.Split( ))[0] +"_" + $permission.FunctionName)
        New-ADGroup -Description ($permission.Functionset + " " + $permission.FunctionName) -Name $t1groupname -Path $Tier1GroupLocation -GroupCategory Security -GroupScope Global -Server $dc
        $adgroup = get-adgroup $t1groupname -Server $DC
        #================================================================================
        #SET ACLS if first word of functionset equals a value in $permissionstoOUmapping
            if ($PermissionsToOUMapping.keys -contains ($permission.FunctionSet.Split( ))[0]){
                #apply GPO Set of Permissions and OU set of permissions to the Code level OU not the sub OUs
                if (($permission.FunctionSet.Split( ))[0] -eq "OU"){
                    $t1OU = "OU="+ $code + "," + $toplevelTier1OUDN
                    $t1ou = Get-ADOrganizationalUnit $t1ou
                    #createcomputeraccount -objGroup $adgroup -objOU $ou -inheritanceType "Descendents"
                    iex ($permission.FunctionName + " -objgroup " + '$adgroup' + " -objou " + '$t1OU' + " -inheritanceType `'Descendents`'")
                }
                
                else{
                   $t1OU = "OU="+ $PermissionsToOUMapping[($permission.FunctionSet.Split( ))[0]] +",OU="+ $code + "," + $toplevelTier1OUDN
                    $t1ou = Get-ADOrganizationalUnit $t1ou
                    #createcomputeraccount -objGroup $adgroup -objOU $ou -inheritanceType "Descendents"
                    iex ($permission.FunctionName + " -objgroup " + '$adgroup' + " -objou " + '$t1OU' + " -inheritanceType `'Descendents`'")


                }
                
            }
        #END T1 ACLs
        #BEGIN T2 Group creation and ACLs
        $t2groupname = ($code+ "_T2_" +($permission.FunctionSet.Split( ))[0] +"_" + $permission.FunctionName)
        New-ADGroup -Description ($permission.Functionset + " " + $permission.FunctionName) -Name $t2groupname -Path $Tier2GroupLocation -GroupCategory Security -GroupScope Global -Server $dc
        $adgroup = get-adgroup $t2groupname -Server $dc
        #================================================================================
        #SET ACLS if first word of functionset equals a value in $permissionstoOUmapping
            if ($PermissionsToOUMapping.keys -contains ($permission.FunctionSet.Split( ))[0]){
                if(($permission.FunctionSet.Split( ))[0] -eq "OU"){
                    $t2OU = "OU="+ $code + "," + $toplevelTier2OUDN
                    $t2OU = Get-ADOrganizationalUnit $t2OU
                    iex ($permission.FunctionName + " -objgroup " + '$adgroup' + " -objou " + '$t2OU' + " -inheritanceType `'Descendents`'")

                }
                else{
                    $t2OU = "OU="+ $PermissionsToOUMapping[($permission.FunctionSet.Split( ))[0]] +",OU="+ $code + "," + $toplevelTier2OUDN
                    $t2OU = Get-ADOrganizationalUnit $t2OU
                    iex ($permission.FunctionName + " -objgroup " + '$adgroup' + " -objou " + '$t2OU' + " -inheritanceType `'Descendents`'")
                }
                
            }
        }
    }
    $x++
}

