#!/usr/bin/env python3

import json
import sys
from pprint import pprint

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} callfile1.json callfile2.json")
    sys.exit(1)

verbose = False
file1, file2 = sys.argv[1], sys.argv[2]

with open(file1, "r", encoding="utf-8") as f:
    data1 = json.load(f)

with open(file2, "r", encoding="utf-8") as f:
    data2 = json.load(f)

KEY = "from"
# map all functions by name
map1 = {obj[KEY]: obj for obj in data1}
map2 = {obj[KEY]: obj for obj in data2}

added = []
removed = []
unchanged = []
more_calls_in_fn1 = []
more_calls_in_fn2 = []
distinct_calls = []

for k in map2:
    if k not in map1:
        added.append(map2[k])
        continue
    to_set1 = set(map1[k]["to"])
    to_set2 = set(map2[k]["to"])
    if to_set1.intersection(to_set2) == to_set1 == to_set2:
        unchanged.append(k)
    else:
        diff12 = to_set1.difference(to_set2)
        diff21 = to_set2.difference(to_set1)
        if len(to_set1) > len(to_set2):
            more_calls_in_fn1 += [
                k
                + f" has {len(diff12)} (of {len(to_set1) - len(to_set2)}) more calls: "
                + ",".join(diff12)
            ]
        elif len(to_set1) < len(to_set2):
            more_calls_in_fn2 += [
                k
                + f" has {len(diff21)} (of {len(to_set2) - len(to_set1)}) more calls: "
                + ",".join(diff21)
            ]
        if to_set1.symmetric_difference(to_set2):
            distinct_calls += [
                k
                + f" \n\t\tonly in {file1}: "
                + ",".join(diff12)
                + f" \n\t\tonly in {file2}: "
                + ",".join(diff21)
            ]

for k in map1:
    if k not in map2:
        removed.append(map1[k])

if verbose:
    print("\n=== Unchanged ===")
    pprint(unchanged)

print("\n=== Added ===")
pprint(added)

print("\n=== Removed ===")
pprint(removed)

print("\n=== Different ===")
more_f1_equal = 100 * len(more_calls_in_fn1) / max(len(data1), len(data2))
more_f2_equal = 100 * len(more_calls_in_fn2) / max(len(data1), len(data2))
print(
    f"{len(more_calls_in_fn1)} or {more_f1_equal:.2f}% of functions with more calls found in {file1}: {'\n\t* '.join(more_calls_in_fn1)}"
)
print(
    f"{len(more_calls_in_fn2)} or {more_f2_equal:.2f}% of functions with more calls found in {file2}: {'\n\t* '.join(more_calls_in_fn2)}"
)

distinct_calls_percent = 100 * len(distinct_calls) / max(len(data1), len(data2))
# TODO this is just the two above combined?!
# print(f"{len(distinct_calls)} or {distinct_calls_percent:.2f}% of functions with distinct calls between both files: {"\n\t* ".join(distinct_calls)}")

percent_equal = 100 * len(unchanged) / max(len(data1), len(data2))
# repeat one line resume at the end
print(f"{len(unchanged)} or {percent_equal:.2f} of functions have equal calls in both files")
print(
    f"{len(more_calls_in_fn1)} or {more_f1_equal:.2f}% of functions with more calls found in {file1}"
)
print(
    f"{len(more_calls_in_fn2)} or {more_f2_equal:.2f}% of functions with more calls found in {file2}"
)
# TODO this is just the two above combined?!
# print(f"{len(distinct_calls)} or {distinct_calls_percent:.2f}% of functions with distinct calls between both files")
