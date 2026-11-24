
# Import powershell-yaml if available
if (Get-Module -ListAvailable -Name powershell-yaml) {
    Import-Module powershell-yaml -ErrorAction SilentlyContinue
}

# Import Invoke-AtomicRedTeam if available
$atomicRedTeamModule = Get-Module -ListAvailable -Name invoke-atomicredteam
if ($atomicRedTeamModule) {
    Import-Module invoke-atomicredteam -Force -ErrorAction SilentlyContinue
    $PSDefaultParameterValues = @{"Invoke-AtomicTest:PathToAtomicsFolder"="C:\AtomicRedTeam\atomics"}
}