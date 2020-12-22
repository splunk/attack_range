function Add-TestDrives{
    <#
    .SYNOPSIS
        Adds a powershell drive from your workstation to the domain controller. Port 9389 must be open from your machine to this DC
    
    .DESCRIPTION
        By specifying the machines IP you can connect to the machine and run remote commands on the test domain
    
    
    .EXAMPLE
        PS C:\> Add-TestDrives
        PS C:\> Add-TestDrives -TestDC 10.0.0.123 #connects  to the specified domain controller IP
        PS C:\> Add-TestDrives -TestDC 10.1.1.20 -TestDN badblood.com -Testname 'TestAD'
 
    
    .NOTES
               
        Unless required by applicable law or agreed to in writing, software
        distributed under the License is distributed on an "AS IS" BASIS,
        WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
        See the License for the specific language governing permissions and
        limitations under the License.
        
        Author's blog: https://www.secframe.com

    
#>
    [CmdletBinding()]

param
(
    [Parameter(Mandatory = $false,
        Position = 1,
        HelpMessage = 'Add IP or DNSName of your Domain Controller')]
    [Alias('creds')]
    [System.String]$TestDC = '10.1.1.10',
    [Parameter(Position = 2,
        HelpMessage = 'Specify the DN for the domain')]
        [System.String]$TestDN = 'domain.com',
    [Parameter(Mandatory = $false,
        Position = 3,
        HelpMessage = 'Use this if you want to specify a drive variable')]
    [System.String]$TestName = 'domain'
)
$ADmod = get-module -name activedirectory
if(!$admod){import-module activedirectory}else{}

    #Name of Drive to spit out later in a write host
    $TestFullName = $Testname + ':'
    
    #What level of domain is this
    $level = "Production"
    
        if (!$domain){
            $domain = $testfullname
            $onscreen = 'Attempting to connect to ' + $testdc + '. Connecting to domain named: ' + $testdn
        }
        
        write-host $onscreen -ForegroundColor Yellow
       
        If (!(Test-Path $TestFullNAME)){New-PSDrive -Name $TestName -PSProvider ActiveDirectory -Server $testDC -Root "//RootDSE/" -scope Global -Credential $TestDN\}
        
            If ((Test-Path $TestFullNAME))
            {
                
                Write-host To change to $level $TestDN $ type `'cd $testfullname`' -f Green
             }else{}
        
        }
    Add-TestDrives