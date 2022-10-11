{
  "type": "local",
  "sleep": 0,
  "playbooks": [
    {
      "name": "OS Credential Dumping",
      "enabled": true,
      "tasks": [
        {
          "name": "Lsass Process Dump using Win32 API MiniDumpWriteDump",
          "technique_id": "T1003.001"
        }
      ]
    }
  ]
}