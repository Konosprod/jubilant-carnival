import requests
import argparse
import http.cookiejar
from tqdm.auto import tqdm
import shutil
import pathlib
import zipfile
from PIL import Image
import ffmpeg
import re
import time
import pathvalidate

ugoira_url = "https://www.pixiv.net/ajax/illust/[ugoiraID]/ugoira_meta?lang=en"
illust_url = "https://www.pixiv.net/ajax/illust/[illustID]/pages?lang=en"
user_url = "https://www.pixiv.net/ajax/user/[userID]/profile/all?lang=en"
artwork_url = "https://www.pixiv.net/en/artworks/"
serie_url = "https://www.pixiv.net/ajax/series/[serieID]?lang=en&p="

regex = re.compile("(?P<id>\d+)")


headers = {"Referer": "https://www.pixiv.com",
           "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/81.0"}
s = requests.Session()
s.headers = headers


def download_file(url, path):
    with s.get(url, stream=True) as r:
        total_length = int(r.headers.get("Content-Length", 0))

        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="") as raw:
            with open(path, "wb") as output:
                shutil.copyfileobj(raw, output)


def get_illust(url, quality="original", directory=""):

    if quality == None:
        quality = "original"

    illust_id = regex.search(url).group("id")
    ajax_url = illust_url.replace("[illustID]", illust_id)
    response = s.get(ajax_url).json()

    base_dir = directory / pathlib.Path(illust_id)
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

    imgList[0].save(base_dir.joinpath(ugoira_id+".gif"), format="GIF",
                    append_images=imgList[1:], duration=durationList, loop=0, save_all=True)

    return


def convert_mp4(ugoira_id, response, base_dir):

    concat_text = ""

    for frame in response["body"]["frames"]:
        concat_text += "file \'"+str(base_dir.joinpath(frame["file"]))+"\'\nduration " + str(
            divmod(frame["delay"] / 1000, 60)[1]) + "\n"

    concat_text += "file \'" + \
        str(base_dir.joinpath(response["body"]["frames"][-1]["file"])) + "\'"

    f = open(base_dir.joinpath("tmp.txt"), "w")
    f.write(concat_text)
    f.close()

    ffmpeg.input(base_dir.joinpath("tmp.txt"), format="concat", safe=0).output(str(
        base_dir.joinpath(ugoira_id+".mp4")), c="copy", **{'vsync': 'vfr', 'loglevel': 'quiet'}).run()

    base_dir.joinpath("tmp.txt").unlink(missing_ok=True)

    return


def get_ugoira(url, quality="originalSrc", convertGif=False, convertMp4=False, cleanup=True, directory=""):

    if quality == None:
        quality = "originalSrc"

    ugoira_id = regex.search(url).group("id")
    ajax_url = ugoira_url.replace("[ugoiraID]", ugoira_id)
    response = s.get(ajax_url).json()

    base_dir = directory / pathlib.Path(ugoira_id)
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


def check_ugoira(url):
    id = regex.search(url).group("id")

    ajax_url = ugoira_url.replace("[ugoiraID]", id)
    return not s.get(ajax_url).json()["error"]


def get_user(url, video_quality="originalSrc", convertGif=False, convertMp4=False, cleanup=True, image_quality="original"):

    user_id = regex.search(url).group("id")
    ajax_url = user_url.replace("[userID]", user_id)
    response = s.get(ajax_url).json()

    base_dir = pathlib.Path(user_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    illusts = response["body"]["illusts"]

    if len(illusts) > 0:
        for illust in illusts:
            if check_ugoira(illust):
                get_ugoira(artwork_url + illust, quality=video_quality, convertGif=convertGif,
                           convertMp4=convertMp4, cleanup=cleanup, directory=str(base_dir))
            else:
                get_illust(artwork_url + illust, quality=image_quality, directory=str(base_dir))
            time.sleep(1)

    return

def get_serie(url, image_quality):

    serie_id = regex.findall(url)[1]
    ajax_url = serie_url.replace("[serieID]", serie_id)
    page = 1
    base_dir = ""

    response = s.get(ajax_url + str(page)).json()
    title = response["body"]["illustSeries"][0]["title"]
    base_dir = pathlib.Path(pathvalidate.sanitize_filepath(title))
    base_dir.mkdir(parents=True, exist_ok=True)
    total = response["body"]["illustSeries"][0]["total"]
    total_page = (total+12-1) // 12 +1

    for dummy in range(1, total_page):
        pages = response["body"]["page"]["series"]
        for page in pages:
            output_dir = base_dir / str(page["order"])
            
            if check_ugoira(artwork_url + page["workId"]):
                get_ugoira(artwork_url + page["workId"])
            else:
                get_illust(artwork_url + page["workId"], image_quality, output_dir)

        response = s.get(ajax_url + str(dummy+1)).json()

    return

def main():
    parser = argparse.ArgumentParser("pixiv download")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--illust", help="Illustration url")
    group.add_argument("-u", "--ugoira", help="Ugoira url")
    group.add_argument("-b", "--backup", help="User profile url")
    group.add_argument("-s", "--serie", help="Serie's url")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--video", help="Convert ugoira to video", action="store_true")
    group.add_argument(
        "-g", "--gif", help="Convert ugoira to gif", action="store_true")
    parser.add_argument(
        "-c", "--cookies", help="File containing cookies exported for your browser while beiing logged in pixiv", required=True)
    parser.add_argument(
        "-k", "--clean-up", help="Clean up useless files when converting ugoiras", action="store_true")
    parser.add_argument("--illust-quality", help="Specify the quality of the downloaded file. Can either be [thumb_mini|small|regular|original]. Default is max quality", choices=[
                        "thumb_mini", "small", "regular", "original"], default=None)
    parser.add_argument(
        "--ugoira-quality", help="Specify the quality of the downloaded file. Can either be [src|originalSrc]. Default is max quality", choices=["src", "originalSrc"], default=None)

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
        get_ugoira(args.ugoira, convertMp4=args.video,
                   cleanup=args.clean_up, convertGif=args.gif, quality=args.quality)

    if args.backup:
        get_user(args.backup, convertMp4=args.video, cleanup=args.clean_up, convertGif=args.gif,
                 video_quality=args.ugoira_quality, image_quality=args.illust_quality)

    if args.serie:
        get_serie(args.serie, image_quality=args.illust_quality)

    return


if __name__ == "__main__":
    main()
