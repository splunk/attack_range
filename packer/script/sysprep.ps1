# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
# http://aws.amazon.com/asl/
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

<#
.SYNOPSIS

	Start sysprep with answer file provided in the current directory.
.DESCRIPTION

    Ensure Unattend.xml is located under Sysprep directory.

.PARAMETER NoShutdown

    NoShutdown prevents sysprep to shutdown the instance.
.EXAMPLE
    ./SysprepInstance
#>
param (
    [parameter(Mandatory=$false)]
    [switch] $NoShutdown
)

Set-Variable rootPath -Option Constant -Scope Local -Value (Join-Path $env:ProgramData -ChildPath "Amazon\EC2-Windows\Launch")
Set-Variable modulePath -Option Constant -Scope Local -Value (Join-Path $rootPath -ChildPath "Module\Ec2Launch.psd1")
Set-Variable scriptPath -Option Constant -Scope Local -Value (Join-Path $PSScriptRoot -ChildPath $MyInvocation.MyCommand.Name)
Set-Variable sysprepResDir -Option Constant -Scope Local -Value (Join-Path $rootPath -ChildPath "Sysprep")
Set-Variable beforeSysprepFile -Option Constant -Scope Local -Value (Join-Path $sysprepResDir -ChildPath "BeforeSysprep.cmd")
Set-Variable answerFilePath -Option Constant -Scope Local -Value (Join-Path $sysprepResDir -ChildPath "Unattend.xml")
Set-Variable sysprepPath -Option Constant -Scope Local -Value (Join-Path $env:windir -ChildPath "System32\Sysprep\Sysprep.exe")

# Import Ec2Launch module to prepare to use helper functions.
Import-Module $modulePath

# Check if answer file is located in correct path.
if (-not (Test-Path $answerFilePath))
{
    throw New-Object System.IO.FileNotFoundException("{0} not found" -f $answerFilePath)
}

if (-not (Test-Path $sysprepPath))
{
    throw New-Object System.IO.FileNotFoundException("{0} not found" -f $sysprepPath)
}

# Update the unattend.xml.
try
{
    # Get the locale and admin name to update unattend.xml
    $localAdmin = Get-CimInstance -ClassName Win32_UserAccount | Where-Object {$_.LocalAccount -eq $true -and $_.SID -like 'S-1-5-21-*' -and $_.SID -like '*-500'}
    $localAdminName = $localAdmin.Name
    $locale = ([CultureInfo]::CurrentCulture).IetfLanguageTag

    # Get content as xml
    $content = [xml](Get-Content $answerFilePath)

    # Search for empty locales and assign the correct locale for current OS
    $localeTarget = ($content.unattend.settings | where {$_.pass -ieq 'oobeSystem'}).component | `
                    where {$_.name -ieq 'Microsoft-Windows-International-Core'}
    if ($localeTarget.InputLocale -eq '') { $localeTarget.InputLocale = $locale }
    if ($localeTarget.SystemLocale -eq '') { $localeTarget.SystemLocale = $locale }
    if ($localeTarget.UILanguage -eq '') { $localeTarget.UILanguage = $locale }
    if ($localeTarget.UserLocale -eq '') { $localeTarget.UserLocale = $locale }

    # Search for the first empty RunSynchronousCommand and assign the correct command for current OS
    $adminTarget = (($content.unattend.settings | where {$_.pass -ieq 'specialize'}).component | `
                    where {$_.name -ieq 'Microsoft-Windows-Deployment'}).RunSynchronous | `
                    Foreach {$_.RunSynchronousCommand | where {$_.Order -eq 1 }}
    if ($adminTarget.Path -eq '') { $adminTarget.Path = "net user {0} /ACTIVE:NO /LOGONPASSWORDCHG:NO /EXPIRES:NEVER /PASSWORDREQ:NO" -f $localAdmin.Name }

    # Save the final xml content
    $content.Save($answerFilePath)
}
catch
{
    Write-Warning "Failed to update the custom answer file. Ignore this message if you modified the file."
}

# Clear instance information from wallpaper.
try
{
    Clear-Wallpaper
}
catch
{
    Write-Warning ("Failed to update the wallpaper: {0}" -f $_.Exception.Message)
}

# Unregister userdata scheduled task.
try
{
    Invoke-Userdata -OnlyUnregister
}
catch
{
    Write-Warning ("Failed to unreigster the userdata scheduled task: {0}" -f $_.Exception.Message)
}

# Perform commands in BeforeSysprep.cmd.
if (Test-Path $beforeSysprepFile)
{
    Invoke-Item $beforeSysprepFile
}

Start-Process -FilePath $sysprepPath -ArgumentList ("/oobe /quit /generalize `"/unattend:{0}`"" -f $answerFilePath) -Wait -NoNewWindow
