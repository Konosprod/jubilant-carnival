# jubilant-carnival
Download from pixiv.

## Installation

This program requires few libs, you can install everything with :
`python3 -m pip install -r requirements.txt`

## How to use

You first have to get your cookies from pixiv while being logged in, because the program use ajax calls that requires the user to be logged in. You can look for browser extension to get the cookies.

All files are downloaded in their own directories.

Once you got them, you can use the program as follow :

### Download an illustration

* Download an illustration with max quality

`python main.py -i "https://www.pixiv.net/en/artworks/94627049"`

* Download an illustration with thumbnail only

`python main.py -i "https://www.pixiv.net/en/artworks/103030454" -q thumb_mini`

### Download an animation

* Download an animation without converting it (getting all the frames only), with the low resolution

`python main.py -u "https://www.pixiv.net/en/artworks/103175508" -q src`

* Download an animation, converting it in a gif, without cleaning up (keeping all the frames as single files too)

`python main.py -u "https://www.pixiv.net/en/artworks/103094262" -g`

* Download an animation, converting it in a video file, cleaning all the frames, keeping only the video file

`python main.py -u "https://www.pixiv.net/en/artworks/103076903" -v -k`

## Future updates

Maybe i'll add more things in the futur, such as novel downlading too.


