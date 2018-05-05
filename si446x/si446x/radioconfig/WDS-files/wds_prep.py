#!/usr/bin/env python
import os
import re

def process_include(cwd, line, output):
    match = re.findall(r'("([^"]|"")*")',line)
    if match:
        fn = match[0][0][1:-1] # strip quotes
        with open(os.path.join(cwd, fn),'r') as ifd:
            for il in ifd:
                il = il.replace('\\','/').strip() + '\n'  # remove DOS eol
                output.write(il)
            return True
    return False

def process_config(fname, output):
    with open(fname,'r') as hfd:
        for cl in hfd:
            cl = cl.strip() + '\n'  # remove DOS eol
            if cl.startswith('#include '):
                if process_include(os.path.dirname(fname), cl, output):
                    continue
            output.write(cl)

if __name__ == '__main__':
    for adir in os.listdir(os.path.abspath(os.path.relpath('.'))):
        filepath = os.path.join(adir,
                                'src/application/radio_config.h')
        if os.path.exists(filepath):
            with open(adir+'.h','w') as output:
                process_config(filepath, output)
