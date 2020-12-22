Function CreateGroup{

    
    $setDC = (Get-ADDomain).pdcemulator
    
    #=======================================================================
    #P1
    #set owner and creator here
    
        #p1
        $userlist = get-aduser -ResultSetSize 2500 -Server $setdc -Filter *
        $ownerinfo = get-random $userlist
        
                $adminID = (get-random $userlist).samaccountname
            
    #=======================================================================
    $dn = (get-aduser $ownerinfo).distinguishedname
    
    
            $Description = 'Follow Davidprowe on twitter for updates to this script'
    
    #================================
    # OU LOCATION
    #================================
    $OUsAll = get-adobject -Filter {objectclass -eq 'organizationalunit'} -ResultSetSize 300
    #will work on adding objects to containers later $ousall += get-adobject -Filter {objectclass -eq 'container'} -ResultSetSize 300|where-object -Property objectclass -eq 'container'|where-object -Property distinguishedname -notlike "*}*"|where-object -Property distinguishedname -notlike  "*DomainUpdates*"

                    $ouLocation = (Get-Random $OUsAll).distinguishedname

    #==========================================
    #END OU WORKFLOW
    
    $Groupnameprefix = ''
    $Groupnameprefix = ($ownerinfo.samaccountname).substring(0,2)
    function Get-ScriptDirectory {
        Split-Path -Parent $PSCommandPath
    }
    $groupscriptPath = Get-ScriptDirectory
           
    $application = try{(get-content($groupscriptPath + '\hotmail.txt')|get-random).substring(0,9)} catch{(get-content($groupscriptPath + '\hotmail.txt')|get-random).substring(0,3) }
    $functionint = 1..100|Get-random  
    if($functionint -le 25){$function = 'admingroup'}else{$function = 'distlist'}              
    $GroupNameFull = $Groupnameprefix + '-'+$Application+ '-'+$Function
                                            
    
        $departmentnumber = [convert]::ToInt32('9999999') 
       
    #Append name if duplicate name created
    $i = 1
    do {
        $checkAcct = $null
        
        if($i -gt 1)
            {
            $GroupNameFull = $GroupNameFull + $i
            }
        $i++
        try{$checkAcct = get-adgroup $GroupNameFull}
        catch{}
    
        }
    while($checkAcct -ne $null)
    
    
    
    #=============================================
    #ATTEMPTING TO CREATE GROUP
    #=============================================
    try{New-ADGroup -Server $setdc -Description $Description -Name $GroupNameFull -Path $ouLocation -GroupCategory Security -GroupScope Global -ManagedBy $ownerinfo.distinguishedname}
    catch{#oopsie
    }
        
    #===============================
    #SET ATTRIBUTES
    #===============================
    
    try{
        if ($PSBoundParameters.ContainsKey('Debug') -eq $true)
           {write-host "Attempting to create account line 1050  "}
        $results = Get-adgroup $GroupNameFull -server $setdc 
    
        }
    catch {
        #write-host Group $name was not created:
        #write-host "`t`t`tNew-ADGroup -Server $setdc -Description $Description -Name $GroupNameFull -Path $ouLocation  -GroupCategory Security -GroupScope Global -ManagedBy $ownerinfo.distinguishedname"
        }    
    
      
    
    
    
    }
