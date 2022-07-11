# Control Attack Range
The Attack Range is a detection development platform, which is optimized for fast build and destroy time. This means you can build a fresh Attack Range multiple times a day for various tasks such as detection development, POC, demos and so on. The Attack range supports multiple commands to control the Attack Range.

## Build
Builds a new Attack Range based on your configuration in attack_range.yml
```
python attack_range.py build
```

## Destroy
Destroys an Attack Range and deletes/deprovision all used ressources
```
python attack_range.py destroy
```

## Stop
Stops an Attack Range which will shutdown the instances but not deprovision it
```
python attack_range.py stop
```

## Resume
Resumes a stopped Attack Range
```
python attack_range.py resume
```

## Show
Shows the ressources of an Attack Range
```
python attack_range.py show
```