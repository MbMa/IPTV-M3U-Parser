import argparse
import requests
import re
import os
import json
import datetime

def parse_m3u(m3u_file):
    with open(m3u_file, 'r', encoding='iso-8859-1', errors="ignore") as f:
        m3u_content = f.read()

    channels = re.findall(r'#EXTINF:.*?,(.*?)\n(.*?)\n', m3u_content)

    return channels


def check_channels(channels, wanted_channels):
    accessible_channels = []
    server_ok = False
    for name, url in channels:
        for pattern in wanted_channels:
            if re.search(pattern, name, re.IGNORECASE):
                try:
                    if server_ok == False :
                        r = requests.get(url, timeout=5)
                        if r.status_code == 200:
                            server_ok = True
                            accessible_channels.append((name, url))
                            print(f'Channel {name} is Ok :)')
                        else:
                            print(f'{r.status_code} : Server is not OK :(')
                            accessible_channels.append((name, url))
                            print(accessible_channels[0])
                            return accessible_channels, server_ok
                    else:
                        accessible_channels.append((name, url))
                        print(f'Channel {name} is Ok :)')
                except requests.exceptions.Timeout:
                    print("⚠ Server is slow, skipping channel")
                    pass
                except requests.exceptions.TooManyRedirects:
                    print("⚠ Channel link is bad, skipping channel")
                    pass
                except Exception as e:
                    print("===== FATAL ERROR =====")
                    print(e)
                    pass

    return accessible_channels, server_ok


def save_m3u(output_file, accessible_channels, server_ok):
    if server_ok:
        with open(output_file, 'w', errors="ignore") as f:
            f.write('#EXTM3U\n')
            for name, url in accessible_channels:
                f.write(f'#EXTINF:-1,{name}\n{url}\n')

def player_info(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.content)
            if data['user_info']['auth'] > 0:
                exp_date_timestamp = int(data['user_info']['exp_date']) if data['user_info']['exp_date'] else 0
                exp_date_readable = datetime.datetime.fromtimestamp(exp_date_timestamp).strftime('%Y-%m-%d %H:%M:%S')

                status = data['user_info']['status']
                max_connections = data['user_info']['max_connections']
                created_at_timestamp =int(data['user_info']['created_at'])
                created_at_readable = datetime.datetime.fromtimestamp(created_at_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                active_cons = data['user_info']['active_cons']
                is_trial = data['user_info']['is_trial']

                info = f'{exp_date_readable};{status};{max_connections};{created_at_readable};{active_cons};{is_trial}'
                return info
            print("(i) Account info : User not authentified")
        else:
            print("(i) Account info : Failed to retrieve data from server")
    except Exception as e:
        print(e)
        exit()

def save_hosts(input_filename, output_filename, accessible_channels, server_ok):

    # Regular expression pattern for matching URLs with the specified pattern
    url_pattern = r"http://(\S+)/(\S+)/(\S+)/(\d+)"

    # Initialize a dictionary to store the hosts and their corresponding URLs
    hosts = {}

    if server_ok:
        # Read in the input file and filter lines starting with "http"
        with open(input_filename, "r") as infile:
            for line in infile:
                if line.startswith("http"):
                    # Extract the host, username, password, and number from the URL
                    match = re.search(url_pattern, line)
                    if match:
                        host = match.group(1)
                        username = match.group(2)
                        password = match.group(3)

                        # Check if the host already exists in the dictionary
                        if host not in hosts:
                            # If it doesn't, add the URL to the dictionary
                            url = f"http://{host}/get.php?username={username}&password={password}&type=m3u_plus"
                            json = f"http://{host}/player_api.php?username={username}&password={password}"
                            hosts[host] = (url,json)
    else:
        name, line = accessible_channels[0]
        # Extract the host, username, password, and number from the URL
        match = re.search(url_pattern, line)
        if match:
            host = match.group(1)
            username = match.group(2)
            password = match.group(3)

            # Add the URL to the dictionary
            url = f"http://{host}/get.php?username={username}&password={password}&type=m3u_plus"
            json = f"http://{host}/player_api.php?username={username}&password={password}"
            hosts[host] = (url,json)

    # Write out the new file with the first occurrence of each host
    with open(output_filename, "a+") as outfile:
        outfile.seek(0)
        first_line = outfile.readline().strip()

        # Append header to the output file if it's the first time the file is being written
        if not first_line:
            outfile.write("playlist;info;exp_date_readable;status;max_connections;created_at_readable;active_cons;is_trial\n")
        
        # Read in the existing URLs from the output file
        existing_urls = set(line.strip() for line in outfile)
        # Append new URLs to the output file if the host is not already in the file

        for host, urls in hosts.items():
            if urls[0] not in existing_urls:
                info = player_info(urls[1])
                outfile.write(f"{urls[0]};{urls[1]};{info}\n")


def main():
    parser = argparse.ArgumentParser(description='Extract accessible channels from M3U playlist')
    parser.add_argument('-l', '--local', help='Path to local M3U file')
    parser.add_argument('-r', '--remote', help='URL of remote M3U file')
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-w', '--wanted', help='Path to file containing channel names to extract', default="wanted.txt")
    parser.add_argument('-a', '--accounts', help='Csv file name containing accounts playlists and info', default="accounts.csv")

    args = parser.parse_args()

    output = "output.csv"

    if args.local:
        m3u_file = args.local
        base, ext = m3u_file.split(".")
        output = base  + "_output." + ext

    elif args.remote:
        response = requests.get(args.remote)
        if response.status_code == 200:
            if response.headers["Content-Disposition"]:
                m3u_file = response.headers["Content-Disposition"].split("filename=")[1]
                m3u_file = m3u_file[1:-1]
            else:
                m3u_file = response.url.split("/")[-1]
            with open(m3u_file, "wb") as f:
                f.write(response.content)

            base, ext = m3u_file.split(".")
            output = base  + "_output." + ext

    else:
        parser.error('Please specify either a local or remote M3U file')


    if os.path.isfile(args.wanted):
        with open(args.wanted, 'r') as f:
            wanted_channels = [line.strip() for line in f.readlines()]
            if wanted_channels == []:
                print(f"{args.wanted} is empty")
                exit()
    else:
        print(f"The file of wanted channels {args.wanted} does not exist.")
        exit()
    
    print(r"""
    _____ _____ _________      __   _____        _____   _____ ______ _____  
   |_   _|  __ |__   __\ \    / /  |  __ \ /\   |  __ \ / ____|  ____|  __ \ 
     | | | |__) | | |   \ \  / /   | |__) /  \  | |__) | (___ | |__  | |__) |
     | | |  ___/  | |    \ \/ /    |  ___/ /\ \ |  _  / \___ \|  __| |  _  / 
    _| |_| |      | |     \  /     | |  / ____ \| | \ \ ____) | |____| | \ \ 
   |_____|_|      |_|      \/      |_| /_/    \_|_|  \_|_____/|______|_|  \_\
                                                                                                                                                 
    """)
    channels = parse_m3u(m3u_file)
    accessible_channels, server_ok = check_channels(channels, wanted_channels)
    save_m3u(output, accessible_channels, server_ok)
    save_hosts(output, args.accounts, accessible_channels, server_ok)

if __name__ == '__main__':
    main()
