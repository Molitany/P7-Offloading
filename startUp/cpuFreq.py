import os
import re
import random

def set_cpu_freq():
    info = os.popen('cpufreq-info').read()
    frequencies_text = re.search('available frequency steps: (.+)\n', info).group(1)
    frequencies = list(map(lambda x: x.replace(' ', ''), frequencies_text.split(',')))
    chosen_frequency = random.choice(frequencies)
    os.popen(f'sudo cpufreq-set -g userspace')
    os.popen(f'sudo cpufreq-set -f {chosen_frequency}')


set_cpu_freq()