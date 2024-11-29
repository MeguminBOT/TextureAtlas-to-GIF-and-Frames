import re
import os

def count_spritesheets(directory):
    return sum(1 for filename in os.listdir(directory) if filename.endswith('.xml') or filename.endswith('.txt'))

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).rstrip()