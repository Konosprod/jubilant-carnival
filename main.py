import sys
import requests
import argparse
import http.cookiejar
from tqdm.auto import tqdm
import shutil
import pathlib
import zipfile
from PIL import Image
import ffmpeg

ugoira_url = "https://www.pixiv.net/ajax/illust/[ugoiraID]/ugoira_meta?lang=en"
illust_url = "https://www.pixiv.net/ajax/illust/[illustID]/pages?lang=en"
headers = {"Referer": "https://www.pixiv.com", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0"}

s = requests.Session()

s.headers = headers


def download_file(url, path):
    with s.get(url, stream=True) as r:
        total_length = int(r.headers.get("Content-Length", 0))

        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
            with open(path, "wb") as output:
                shutil.copyfileobj(raw, output)

def get_illust(url, quality="original"):

    if quality == None:
        quality = "original"

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

def convert_gif(ugoira_id, response, base_dir):
    imgList = []
    durationList = []
    for frame in response["body"]["frames"]:
        imgList.append(Image.open(base_dir.joinpath(frame["file"])))
        durationList.append(frame["delay"])

    imgList[0].save(base_dir.joinpath(ugoira_id+".gif"), format="GIF", append_images=imgList[1:], duration=durationList, loop=0, save_all=True)

    return

def convert_mp4(ugoira_id, response, base_dir):

    concat_text = ""

    for frame in response["body"]["frames"]:
        concat_text += "file \'"+str(base_dir.joinpath(frame["file"]))+"\'\nduration " + str(divmod(frame["delay"] / 1000, 60)[1]) + "\n"

    concat_text += "file \'" + str(base_dir.joinpath(response["body"]["frames"][-1]["file"])) + "\'"

    f = open(base_dir.joinpath("tmp.txt"), "w")
    f.write(concat_text)
    f.close()

    ffmpeg.input(base_dir.joinpath("tmp.txt"), format="concat", safe=0).output(str(base_dir.joinpath(ugoira_id+".mp4")), c="copy", **{'vsync':'vfr', 'loglevel': 'quiet'}).run()

    base_dir.joinpath("tmp.txt").unlink(missing_ok=True)

    return

def get_ugoira(url, quality="originalSrc", convertGif=False, convertMp4=False, cleanup=True):

    if quality == None:
        quality = "originalSrc"

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

    if convertGif:
        print("Building gif file")
        convert_gif(ugoira_id, response, base_dir)

    if convertMp4:
        print("Building mp4 file")
        convert_mp4(ugoira_id, response, base_dir)

    if cleanup:
        files = base_dir.glob("*.jpg")
        for file in files:
            file.unlink()

    path.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser("pixiv download")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--illust", help="Illustration url")
    group.add_argument("-u", "--ugoira", help="Ugoira url")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--video", help="Convert ugoira to video", action="store_true")
    group.add_argument("-g", "--gif", help="Convert ugoira to gif", action="store_true")
    parser.add_argument("-c", "--cookies", help="File containing cookies exported for your browser while beiing logged in pixiv", required=True)
    parser.add_argument("-k", "--clean-up", help="Clean up useless files when converting ugoiras", action="store_true")
    parser.add_argument("-q", "--quality", help="Specify the quality of the downloaded file. Can either be [thumb_mini|small|regular|original] for illustration or [src|originalSrc] for ugoiras. Default is max quality", default=None)

    args = parser.parse_args()

    if args.cookies:
        if not pathlib.Path(args.cookies).exists():
            print("You have to specify a valid cookie file !")
            return
    
    cj = http.cookiejar.MozillaCookieJar(args.cookies)
    cj.load(ignore_expires=True)
    s.cookies = cj

    if args.illust:
        get_illust(args.illust, quality=args.quality)

    if args.ugoira:
        get_ugoira(args.ugoira, onvertMp4=args.video, cleanup=args.clean_up, convertGif=args.gif, quality=args.quality)
    return


if __name__ == "__main__":
    main()