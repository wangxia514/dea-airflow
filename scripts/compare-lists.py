#!/usr/bin/env python

import os
import sys

import humanize
import psutil

process = psutil.Process(os.getpid())
file1 = sys.argv[1]
file2 = sys.argv[2]

print(f"Computing {file1} - {file2}", file=sys.stderr)

with open(sys.argv[1]) as fin:
    set1 = set(l.strip() for l in fin.readlines())

with open(sys.argv[2]) as fin:
    set2 = set(l.strip() for l in fin.readlines())

print(f"len(set1) = {len(set1)}, len(set2) = {len(set2)}", file=sys.stderr)

# or
# import resource
# resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(f"Current RAM: {humanize.naturalsize(process.memory_info().rss)}", file=sys.stderr)

for l in sorted(set1 - set2):
    print(l)
