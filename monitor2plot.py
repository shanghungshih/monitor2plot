import matplotlib.pyplot as plt
import numpy as np
import psutil
import time
import subprocess
import re
import os
import argparse
import logging
from textwrap import dedent

logger_stderr = logging.getLogger(__name__+'stderr')
logger_stderr.setLevel(logging.INFO)
stderr_handler = logging.StreamHandler()
stderr_handler.setFormatter(logging.Formatter('%(levelname)-8s %(message)s'))
logger_stderr.addHandler(stderr_handler)
logger_null = logging.getLogger(__name__+'null')
null_handler = logging.NullHandler()
logger_null.addHandler(null_handler)

VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION[0:3])) + ''.join(VERSION[3:])

def getInfo(p, pid_id, interval):
    try:
        process = psutil.Process(pid_id)
        threads = process.num_threads()
        cpu_percent = process.cpu_percent(interval=interval)
        cpu_times = process.cpu_times()
        mem_percent = process.memory_percent()
        mem_info = process.memory_info()
        return {'threads': threads, 'cpu_percent': cpu_percent, 'cpu_times': cpu_times, 'mem_percent': mem_percent, 'mem_info': mem_info}
    except:
        return

def plot(pid_id, cmd, interval, period, records, theme, output):
    # get minimun amount of data
    def getMin(x, y):
        if len(x) != len(y):
            l = min(len(x), len(y))
            x = x[:l]
            y = y[:l]
        return x, y

    plt.style.use('seaborn-talk') if theme == 'light' else plt.style.use('dark_background')
    plt.figure(figsize=(12, 8)) if theme == 'light' else plt.figure(figsize=(8, 6))

    # CPU
    plt.subplot(2, 1, 1)
    y = [float(i['cpu_percent']) for i in records]
    y.insert(0, 0)   # initial value = 0
    x = np.arange(0, period, interval*2)
    x, y = getMin(x, y)
    plt.plot(x, y, label='CPU')
    cpu_yticks = plt.yticks()[0]
    plt.ylim(0)
    plt.xticks([], [])
    plt.legend()
    plt.ylabel('Percentage (%)')
    # yticks at right-hand side
    ax1 = plt.twinx()
    ax1.set_ylabel('threads')
    ax1.tick_params(axis='y')
    threads_ct = 0
    threads = []
    for i in cpu_yticks[1:-1]:
        if i % 100 == 0:
            threads.append(threads_ct)
            threads_ct += 1
    ax1.set_yticks(threads)
    plt.title('PID: %s\nCPU TIME: %.2f sec\nCMD: %s' %(pid_id, float(re.search('user=(.*?),', str(records[-1]['cpu_times'])).group(1)), cmd), fontsize=12)

    # MEM
    plt.subplot(2, 1, 2)
    y = [float(i['mem_percent']) for i in records]
    y.insert(0, 0)
    x, y = getMin(x, y)
    plt.plot(x, y, color='y', label='MEM')
    mem_yticks = plt.yticks()[0]
    plt.ylim(0)
    plt.legend()
    plt.xlabel('sec')
    plt.ylabel('Percentage (%)')
    # # yticks at right-hand side
    ax2 = plt.twinx()
    ax2.tick_params(axis='y')
    mem_total = psutil.virtual_memory().total
    mem = []
    right_label = 'MB'
    for i in mem_yticks[1:-1]:
        # >= 1G use GB
        if i*mem_total/1024/1204/1024/100 >= 1:
            mem = [i*mem_total/1024/1204/1024/100 for i in mem_yticks[1:-1]]
            right_label = 'GB'
            break
        # < 1G use MB
        mem.append(i*mem_total/1024/1204/100)
    ax2.set_yticks(mem)
    ax2.set_ylabel(right_label)
    plt.savefig(output)

def monitor(cmd, theme, interval, pid_id, output):
    if pid_id is None:
        p = subprocess.Popen(cmd, shell=True)

    pid_id = p.pid if pid_id is None else pid_id
    records = []
    while p.poll() is None:
        values = getInfo(p, pid_id=pid_id, interval=interval)
        if values:
            records.append(values)
            time.sleep(interval)

    try:
        time_used = float(re.search('user=(.*?),', str(records[-1]['cpu_times'])).group(1))
        plot(pid_id, cmd, interval, time_used, records, theme, output)
        logger_stderr.info('PID [%s] finished' %(pid_id))
    except IndexError:
        print('IndexError: list index out of range\nPlease try smaller interval for accessing CPU time')

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=dedent("""\
    Testing environment: Python 3
    Quick start:
    1. Run the program with your command (e.g. ls)
        python3 monitor2plot.py -c "ls"
    * Notes: if the job takes a long time to run, you can specify a greater interval time
    """))
    optional = parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    required.add_argument('-c', '--cmd', type=str, help='the command you would like to monitor')
    optional.add_argument('-o', '--output', type=str, default=os.path.join(os.getcwd(), "monitor2plot.png"), help='output plot name (default: $PWD/monitor2plot.png)')
    optional.add_argument('-p', '--pid', type=int, default=None, help='PID id to monitor (default: None)')
    optional.add_argument('-i', '--interval', type=float, default=0.01, help='time interval for accessing CPU time (default: 0.01 sec)')
    optional.add_argument('-t', '--theme', type=str, default="dark", help='theme for the plot: dark/light (default: dark)')
    optional.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
    parser._action_groups.append(optional)
    args = parser.parse_args()

    if args.cmd is None and args.pid is None:
        parser.print_help()
    else:
        if args.pid is None:
            logger_stderr.info('cmd: [%s]' % (args.cmd))
        else:
            logger_stderr.info('PID id: [%s]' % (args.pid))
        logger_stderr.info('theme: [%s]' % (args.theme))
        logger_stderr.info('interval: [%s]' % (args.interval))
        logger_stderr.info('output: [%s]' % (args.output))
        monitor(cmd=args.cmd, theme=args.theme, interval=args.interval, pid_id=args.pid, output=args.output)


if __name__ == '__main__':
    main()