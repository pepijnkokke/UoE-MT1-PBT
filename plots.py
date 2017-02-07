#!/usr/bin/env python2.7

from itertools import groupby
from matplotlib import pyplot as plt
import re

def chunk(l, n):
    # Partition a list in chunks of size n.
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def parse_conf(conf):
    # Parse a configuration string.
    m = re.match("(.*)\.s=(\d+).k=(\d+)", conf)
    return (int(m.group(2)), int(m.group(3)))

def create_plot(filename):
    with open("data/"+filename+".log", 'r') as data_file:
        data = chunk(data_file.readlines(), 3)
        data = [(parse_conf(conf), float(time), float(score))
                for (conf, time, score) in data]
        data = groupby(data, key=lambda x: x[0][1])


    plt.figure()
    plt.subplot(211)
    plt.yscale('log')
    plt.xscale('log')
    plt.ylabel('time (ms)')
    plt.subplot(212)
    plt.xscale('log')
    plt.ylabel('score (log-probability)')
    plt.xlabel('stack size')

    for (i, group) in data:
        confs, times, scores = zip(*group)
        ss, ks = zip(*confs)
        lbl = 'k=' + str(ks[0])

        plt.subplot(211)
        plt.plot(ss, times, '-', label=lbl)
        plt.subplot(212)
        plt.plot(ss, scores, '-', label=lbl)

    plt.subplot(212)
    plt.legend()

    plt.savefig('fig-' + filename)

create_plot('default')
create_plot('part2')
create_plot('part3')
