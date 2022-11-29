import sys
import requests
import argparse
import http.cookiejar
from tqdm.auto import tqdm
import shutil
import pathlib

ugoira_url = "https://www.pixiv.net/ajax/illust/[UgoiraID]/ugoira_meta?lang=en"
illust_url = "https://www.pixiv.net/ajax/illust/[illustID]/pages?lang=en"
headers = {"Referer": "https://www.pixiv.com", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0"}

s = requests.Session()

s.headers = headers
cj = http.cookiejar.MozillaCookieJar("cookies.txt")
cj.load(ignore_expires=True)
s.cookies = cj

def get_illust(url):
    illust_id = url[url.rindex("/")+1:]
    ajax_url = illust_url.replace("[illustID]", illust_id)
    response = s.get(ajax_url).json()

    base_dir = pathlib.Path(illust_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    for page in response["body"]:
        url = page["urls"]["original"]

        with s.get(url, stream=True) as r:
            total_length = int(r.headers.get("Content-Length", 0))

            with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
                with open(base_dir.joinpath(url[url.rindex("/")+1:]), "wb") as output:
                    shutil.copyfileobj(raw, output)

def main():
    
    get_illust(sys.argv[1])
    return


if __name__ == "__main__":
    main()