# Attack Data
The data generated with the Attack Range can be exported and imported from the Splunk server.

## Dump Attack Data
```
python attack_range.py dump --file_name attack_data/dump.log --search 'index=win' --earliest 2h
```

## Replay Attack Data
```
python attack_range.py replay --file_name attack_data/dump.log --source test --sourcetype test
```