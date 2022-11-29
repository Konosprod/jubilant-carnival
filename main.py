import sys
import requests
import argparse
import http.cookiejar
from tqdm.auto import tqdm
import shutil
import pathlib
import zipfile
from PIL import Image

ugoira_url = "https://www.pixiv.net/ajax/illust/[ugoiraID]/ugoira_meta?lang=en"
illust_url = "https://www.pixiv.net/ajax/illust/[illustID]/pages?lang=en"
headers = {"Referer": "https://www.pixiv.com", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0"}

s = requests.Session()

s.headers = headers
cj = http.cookiejar.MozillaCookieJar("cookies.txt")
cj.load(ignore_expires=True)
s.cookies = cj

def download_file(url, path):
    with s.get(url, stream=True) as r:
        total_length = int(r.headers.get("Content-Length", 0))

        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
            with open(path, "wb") as output:
                shutil.copyfileobj(raw, output)

def get_illust(url, quality="original"):
    illust_id = url[url.rindex("/")+1:]
    ajax_url = illust_url.replace("[illustID]", illust_id)
    response = s.get(ajax_url).json()

    base_dir = pathlib.Path(illust_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    nb_page = len(response["body"])
    print(f"Downloading {nb_page} pages", flush=True)
    for page in response["body"]:
        url = page["urls"][quality]
        path = base_dir.joinpath(url[url.rindex("/")+1:])
        download_file(url, path)

def get_ugoira(url, quality="originalSrc", convert=True):
    ugoira_id = url[url.rindex("/")+1:]
    ajax_url = ugoira_url.replace("[ugoiraID]", ugoira_id)
    response = s.get(ajax_url).json()

    base_dir = pathlib.Path(ugoira_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading archive", flush=True)
    url = response["body"][quality]
    path = base_dir.joinpath(url[url.rindex("/")+1:])
    download_file(url, path)

    print("Extracting archive to tmp path")
    with zipfile.ZipFile(path, "r") as zip_ref:
        zip_ref.extractall(base_dir)

    if convert:
        print("Building gif file")
        imgList = []
        durationList = []
        for frame in response["body"]["frames"]:
            imgList.append(Image.open(base_dir.joinpath(frame["file"])))
            durationList.append(frame["delay"])

        imgList[0].save(base_dir.joinpath(ugoira_id+".gif"), format="GIF", append_images=imgList[1:], duration=durationList, loop=0, save_all=True)

    path.unlink()

def main():

    #get_illust(sys.argv[1])
    #get_ugoira(sys.argv[1], "src")
    return


if __name__ == "__main__":
    main()