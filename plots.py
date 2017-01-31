#!/usr/bin/env python2.7

from math import log
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from mpl_toolkits.mplot3d import Axes3D
import re

def chunk(l, n):
    # Partition a list in chunks of size n.
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def parse_conf(conf):
    # Parse a configuration string.
    m = re.match("(.*)\.s=(\d+).k=(\d+)", conf)
    return (int(m.group(2)), int(m.group(3)))

with open("try-parameters.log", 'r') as data_file:
    data = chunk(data_file.readlines(), 3)
    data = [(parse_conf(conf), float(time), abs(float(score)))
            for (conf, time, score) in data]
    
    min_time = min(time for (_, time, _) in data)
    max_time = max(time for (_, time, _) in data)
    dlt_time = max_time - min_time
    
    min_score = min(score for (_, _, score) in data)
    max_score = max(score for (_, _, score) in data)
    dlt_score = max_score - min_score

    data = [(conf,
             ((time - min_time) / dlt_time * 100.0),
             ((1.0 - ((score - min_score) / dlt_score))) * 100.0)
            for (conf, time, score) in data]


fig = plt.figure('fig-conf-time-score')
ax = fig.add_subplot(111, projection='3d')

for ((s, k), time, score) in data:
    s = log(s)
    k = log(k)
    ax.plot([ s, s ], [ k, k ], [ time, score ], '-')
    ax.scatter([ s ], [ k ], [ time ], color='black')
    ax.scatter([ s ], [ k ], [ score ], color='grey')

fig.savefig('fig-conf-time-score.png')
