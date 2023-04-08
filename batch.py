import subprocess
import argparse
import requests
import os
from time import sleep

parser = argparse.ArgumentParser(description='Extract accessible channels from M3U playlist')
parser.add_argument('-l', '--links', help='Path to the links file', default='links.txt')
args = parser.parse_args()

if not os.path.isfile(args.links):
    print(f"The file {args.links} does not exist.")
    exit()
    
with open(args.links) as file:
        links = file.read().splitlines()
        print(f"===== Batch Script =====")

for link in links:
    try:
        print(f"===== Scrapping Link =====")
        response = requests.get(link, timeout=5)
        status_code = response.status_code
        if status_code == 200:
            print(f"Link is ok : {link}")
            subprocess.run(['python', 'iptv-parser.py', '-r', link])
        else:
            print(f"Link is not ok : {link} - {status_code}")
            sleep(1)
    except requests.exceptions.RequestException as e:
        print(f'{link} - Error: {e}')
    
