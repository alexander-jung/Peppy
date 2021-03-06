# Copyright 2016-2018 Peppy Player peppy.player@gmail.com
# 
# This file is part of Peppy Player.
# 
# Peppy Player is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Peppy Player is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Peppy Player. If not, see <http://www.gnu.org/licenses/>.

import os
import ssl
import codecs
import importlib
import logging
import base64
import hashlib
import pygame
import collections
import urllib
from subprocess import Popen, PIPE
from zipfile import ZipFile
from mutagen.id3 import ID3
from mutagen.flac import FLAC

from ui.state import State
from util.config import Config, USAGE, USE_VOICE_ASSISTANT, COLORS, COLOR_DARK, FONT_KEY, CURRENT, FILE_LABELS, \
    LANGUAGE, FILE_PLAYBACK, NAME, KEY_SCREENSAVER_DELAY_1, KEY_SCREENSAVER_DELAY_3, KEY_SCREENSAVER_DELAY_OFF, \
    FOLDER_LANGUAGES, FILE_FLAG, FOLDER_RADIO_STATIONS, FILE_VOICE_COMMANDS, SCREENSAVER_MENU, USE_WEB, \
    FILE_WEATHER_CONFIG, EQUALIZER, SCREEN_INFO, WIDTH, HEIGHT, COLOR_BRIGHT, COLOR_CONTRAST, COLOR_DARK_LIGHT, \
    COLOR_MUTE, SCRIPTS, FILE_BROWSER, FOLDER_IMAGE_SCALE_RATIO, HIDE_FOLDER_NAME
from util.keys import *
from util.fileutil import FileUtil, FOLDER, FOLDER_WITH_ICON, FILE_AUDIO, FILE_PLAYLIST, FILE_IMAGE, FILE_CD_DRIVE
from urllib import request
from urllib.request import urlopen
from io import BytesIO
from websiteparser.loyalbooks.constants import BASE_URL, LANGUAGE_PREFIX, ENGLISH_USA, RUSSIAN
from screensaver.peppyweather.weatherconfigparser import WeatherConfigParser
from util.discogsutil import DiscogsUtil
from svg import Parser, Rasterizer

IMAGE_VOLUME = "volume"
IMAGE_MUTE = "volume-mute"
IMAGE_SHADOW = "shadow"
IMAGE_SELECTION = "selection"
IMAGE_SELECTED_SUFFIX = "-on"
IMAGE_DISABLED_SUFFIX = "-off"
IMAGE_MUTE_SUFFIX = "-mute"
IMAGE_ABOUT = "about"
IMAGE_LANGUAGE = "language"
IMAGE_RADIO = "radio"
IMAGE_STREAM = "stream"
IMAGE_AUDIOBOOKS = "audiobooks"
IMAGE_SCREENSAVER = "screensaver"
IMAGE_PLAYER = "player"
IMAGE_TIME_KNOB = "time-knob"
IMAGE_BACK = "back"
IMAGE_ABC = "abc"
IMAGE_NEW_BOOKS = "new-books"
IMAGE_BOOK_GENRE = "book-genre"
IMAGE_STAR = "star"

PLAYER_RUNNING = "running"
PLAYER_SLEEPING = "sleeping"

FILE_STATIONS = "stations.m3u"
FILE_STREAMS = "streams.m3u"
FILE_FOLDER = "folder.png"
FILE_FOLDER_ON = "folder-on.png"
FILE_DEFAULT_STATION = "default-station.png"
FILE_DEFAULT_STREAM = "default-stream.png"
FILE_COLON = "colon.png"

EXT_PROPERTIES = ".properties"
EXT_PNG = ".png"
EXT_JPG = ".jpg"
EXT_SVG = ".svg"
EXT_M3U = ".m3u"
EXT_MP3 = ".mp3"
EXT_FLAC = ".flac"

FOLDER_ICONS = "icons"
FOLDER_SLIDES = "slides"
FOLDER_STATIONS = "stations"
FOLDER_STREAMS = "streams"
FOLDER_HOME = "home"
FOLDER_GENRES = "genres"
FOLDER_FONT = "font"
FOLDER_PLAYLIST = "playlist"

PACKAGE_SCREENSAVER = "screensaver"    
ICON_FOLDER = "folder"
ICON_FILE_AUDIO = "audio-file"
ICON_FILE_PLAYLIST = "playlist"
ICON_CD_DRIVE = "cd-player"
FOLDER_SAVER = "saver"
FOLDER_SAVER_TYPE = "type"
FOLDER_SAVER_DELAY = "delay"
PROPERTY_SEPARATOR = "="
PROPERTY_COMMENT_CHAR = "#"
CURRENT_PLAYLIST = "current playlist"
CURRENT_INDEX = "current index"
INDEX = "index"
KEY_GENRE = "genre"
UTF_8 = "utf-8-sig"
FOLDER_BUNDLES = "bundles"
FOLDER_VOICE_ASSISTANT = "voiceassistant"
DEFAULT_CD_IMAGE = "cd.png"
SVG_DEFAULT_COLOR = "#808080"
NUMBERS = {
           "VA_ONE" : 1,
           "VA_TWO" : 2,
           "VA_THREE" : 3,
           "VA_FOUR" : 4,
           "VA_FIVE" : 5,
           "VA_SIX" : 6,
           "VA_SEVEN" : 7,
           "VA_EIGHT" : 8,
           "VA_NINE" : 9,
           "VA_ZERO" : 0}

class Util(object):
    """ Utility class """
    
    def __init__(self, connected_to_internet):
        """ Initializer. Prepares Config object. """
        
        self.connected_to_internet = connected_to_internet               
        self.font_cache = {}
        self.image_cache = {}
        self.voice_commands_cache = {}
        self.cd_titles = {}
        self.cd_track_names_cache = {}
        self.screensaver_cache = {}
        self.image_cache_base64 = {}
        self.svg_cache = {}
        self.album_art_url_cache = {}
        self.config_class = Config()
        self.config = self.config_class.config
        self.screen_rect = self.config_class.screen_rect
        self.config[LABELS] = self.get_labels()
        self.weather_config = self.get_weather_config()
        self.pygame_screen = self.config_class.pygame_screen
        self.file_util = FileUtil(self)
        self.CURRENT_WORKING_DIRECTORY = os.getcwd()
        self.read_storage()
        self.discogs_util = DiscogsUtil(self.k1)
        self.COLOR_MAIN = self.color_to_hex(self.config[COLORS][COLOR_BRIGHT])
        self.COLOR_ON = self.color_to_hex(self.config[COLORS][COLOR_CONTRAST])
        self.COLOR_OFF = self.color_to_hex(self.config[COLORS][COLOR_DARK_LIGHT])
        self.COLOR_MUTE = self.color_to_hex(self.config[COLORS][COLOR_MUTE])        
        if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)): 
            ssl._create_default_https_context = ssl._create_unverified_context
        self.podcasts_util = None
    
    def get_labels(self):
        """ Read labels for current language
        
        :return: labels dictionary
        """
        return self.get_labels_by_language(self.config[CURRENT][LANGUAGE])

    def get_labels_by_language(self, language):
        """ Read labels for the provided language

        :param language: provided language

        :return: labels
        """
        path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, language, FILE_LABELS)
        return self.get_properties(path)
    
    def get_voice_commands(self):
        """ Return voice commands for current language """
        
        lang = self.get_current_language()
        
        try:
            return self.voice_commands_cache[lang[NAME]]
        except:
            pass
        
        path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, lang[NAME], FILE_VOICE_COMMANDS)
        voice_commands = self.load_properties(path, UTF_8)
        voice_commands.update(NUMBERS)
        
        self.voice_commands_cache[lang[NAME]] = voice_commands
        
        return voice_commands
    
    def get_weather_config(self):
        """ Read weather config for the current language
        
        :return: weather config
        """
        current_language = self.config[CURRENT][LANGUAGE] 
        path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, current_language)
        parser = WeatherConfigParser(path)
        return parser.weather_config
    
    def get_properties(self, folder):
        """ Read properties file from specified folder
        
        :param folder: folder name
        :return: labels dictionary
        """        
        labels = self.load_properties(folder, UTF_8)
        return labels
    
    def get_voice_assistant_language_code(self, language):
        """ Return the language code required by voice assistant
        
        :param language: current language
        :return: language code
        """
        code = None
        if language == "English-USA":
            code = "en-US"
        elif language == "German":
            code = "de-DE"
        elif language == "French":
            code = "fr-FR"
        elif language == "Italian":
            code = "it-IT"
        elif language == "Japanese":
            code = "ja-JP"
        elif language == "Korean":
            code = "ko-KR"
        elif language == "Spanish":
            code = "es-ES"
        elif language == "Portuguese":
            code = "pt-BR"
        return code
    
    def load_image(self, path, base64=False, bounding_box=None):
        """ Load and return image
        
        :param path: image path 
        :param base64: True - encode image using base64 algorithm (for web), False - don't encode
        :param bounding_box: bounding box 
        """
        if base64:
            return self.load_base64_image(path)
        else:
            return self.load_pygame_image(path, bounding_box)
    
    def load_pygame_image(self, path, bounding_box=None, use_cache=True):
        """ Load image. 
        First, check if image is in the cache.
        If yes, return the image from the cache.
        If not load image file and place it in the cache.
        
        :param path: image path
        :param bounding_box: bounding box
        :param use_cache: True - use cache, False - don't use cache
        
        :return: tuple where the first element is the path to the image and the second element is the image itself
        """
        image = None

        if use_cache:
            try:
                p = path
                if bounding_box:
                    p = path + str(bounding_box[0])
                i = self.image_cache[p]
                return (path, i)
            except KeyError:
                pass
            
        try:            
            image = pygame.image.load(path.encode("utf-8")).convert_alpha()            
        except Exception:
            pass
            
        if image:
            img = image
            p = path
            if bounding_box:
                scale_ratio = self.get_scale_ratio(bounding_box, img)
                img = self.scale_image(image, scale_ratio)
                p = path + str(bounding_box[0])
            if use_cache:
                self.image_cache[p] = img
            return (path, img)
        else:
            return None

    def get_image_from_audio_file(self, filename, return_buffer=False):
        """ Fetch image from audio file. Only MP3 and FLAC supported

        :param filename: file name
        :param return_buffer: True - return image buffer, False - return Pygame image
        :return: image or None if not found
        """
        if not filename: return None

        name = filename.lower()

        if name.endswith(EXT_MP3):
            return self.get_image_from_mp3(filename, return_buffer)
        elif name.endswith(EXT_FLAC):
            return self.get_image_from_flac(filename, return_buffer)
        else:
            return None

    def get_image_from_mp3(self, filename, return_buffer=False):
        """ Fetch image from mp3 file

        :param filename: file name
        :param return_buffer: True - return image buffer, False - return Pygame image
        :return: image or None if not found
        """
        try:
            tags = ID3(filename)
        except:
            return None

        if tags and tags.get("APIC:"):
            try:
                data = tags.get("APIC:").data
                buffer = BytesIO(data)
                if return_buffer:
                    return buffer
                else:
                    return pygame.image.load(buffer).convert_alpha()
            except:
                return None
        else:
            return None

    def get_image_from_flac(self, filename, return_buffer=False):
        """ Fetch image from flac file

        :param filename: file name
        :param return_buffer: True - return image buffer, False - return Pygame image
        :return: image or None if not found
        """
        try:
            pictures = FLAC(filename).pictures
            if pictures:
                data = pictures[0].data
                buffer = BytesIO(data)
                if return_buffer:
                    return buffer
                else:
                    return pygame.image.load(buffer).convert_alpha()
            else:
                return None
        except:
            return None

    def get_scale_ratio(self, bounding_box, img, fit_height=False):
        """ Return scale ratio calculated from provided constraints (bounding box) and image
        
        :param bounding_box: bounding box
        :param img: image
        :param fit_height: True - fit image height to bounding box
        
        :return: tuple representing scale ratio 
        """
        w = bounding_box[0]
        h = bounding_box[1]
        width = img.get_size()[0]
        height = img.get_size()[1]
        
        if width > w and height > h:
            k1 = w/width
            k2 = h/height                                
            if fit_height:
                width = int(width * k2)
                height = int(height * k2)
            else:
                width = int(width * (min(k1, k2)))
                height = int(height * (min(k1, k2)))
        elif width > w and height < h:
            k = w/width
            width = int(width * k)
            height = int(height * k)
        elif width < w and height > h:
            k = h/height
            width = int(width * k)
            height = int(height * k)
        elif width < w and height < h:
            k1 = w/width
            k2 = h/height                                
            width = int(width * (min(k1, k2)))
            height = int(height * (min(k1, k2)))
        return (width, height)        
        
    def load_base64_image(self, path, cache_key=None):
        """ Load image and encode it using base64 encoding.

        :param path: image path
        :param cache_key: cache key
        
        :return: base64 encoded image
        """        
        try:
            img = self.image_cache_base64[path]
            return img
        except:
            pass

        key = path
        if cache_key:
            key = cache_key
        
        if EXT_SVG in path:
            svg_image = self.svg_cache[path]
            img = base64.b64encode(svg_image.encode()).decode()
            self.image_cache_base64[key] = img
            return img
        else:
            if path.lower().endswith(EXT_MP3) or path.lower().endswith(EXT_FLAC):
                image_buffer = self.get_image_from_audio_file(path, True)
                if image_buffer:
                    img = base64.b64encode(image_buffer.read()).decode()
                    self.image_cache_base64[key] = img
                    return img

            with open(path, 'rb') as f:
                img = base64.b64encode(f.read()).decode()
                self.image_cache_base64[key] = img
                return img
    
    def is_cached_svg_image(self, key):
        """ Define if provided image key is the key of the cached SVG image
        
        :patam key: image dictionary key
        
        :return: True - image in cache, False - image not in cache
        """
        if key.endswith(self.COLOR_MAIN) or key.endswith(self.COLOR_ON) or key.endswith(self.COLOR_OFF) or key.endswith(self.COLOR_MUTE):
            return True
        else:
            return False
        
    def load_screensaver_images(self, folder):
        """ Load screensaver images (e.g. for Slideshow plug-in)
        
        :param folder: new image folder
        
        :return: list of images
        """
        slides = []        
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            img = self.load_image(path)
            if img:
                slides.append(img)     
        return slides
    
    def load_background_images(self, folder):
        """ Load background images
        
        :param folder: images folder 
        """
        image_files = self.load_screensaver_images(folder)
        w = self.config[SCREEN_INFO][WIDTH]
        h = self.config[SCREEN_INFO][HEIGHT]
        images = []
        for image in image_files:
            width = image[1].get_size()[0]
            height = image[1].get_size()[1]
            
            if width == w and height == h:
                images.append(image)
            else:
                scale_ratio = self.get_scale_ratio((w, h), image[1], True)
                img = self.scale_image(image[1], scale_ratio)
                t = (image[0], img)
                images.append(t)
        
        return images
        
    def load_station_icon(self, folder, index):
        """ Load station icon
        
        :param folder: image folder
        :param index: image filename without extension        
        :return: station icon
        """
        path = os.path.join(folder, str(index) + EXT_PNG)
        return self.load_image(path)
    
    def load_mono_svg_icon(self, filename, color, bounding_box=None, scale=1.0):
        """ Load monochrome SVG image with replaced color
        
        :param filename: svg image file name
        :param color: base icon hex color
        :param bounding_box: image bounding box
        :param scale: scale factor
        
        :return: bitmap image rasterized from svg image
        """ 
        filename += EXT_SVG
        path = os.path.join(FOLDER_ICONS, filename)
        t = path.replace('\\','/')
        cache_path = t + "_" + str(scale) + "_" + color
        
        try:
            i = self.image_cache[cache_path]
            return (cache_path, i)
        except KeyError:
            pass
        
        s = codecs.open(path, "r").read()
        s = s.replace(SVG_DEFAULT_COLOR, color)
        
        try:
            bitmap_image = Parser.parse(s)
        except:
            logging.debug("Problem parsing file %s", path)
            return None
        
        if self.config[USAGE][USE_WEB]:
            self.svg_cache[cache_path] = s
        
        return self.scale_svg_image(cache_path, bitmap_image, bounding_box, scale)
    
    def load_svg_icon(self, filename, bounding_box=None, scale=1.0):
        """ Load SVG image
        
        :param filename: svg image file name
        :param bounding_box: image bounding box
        :param scale: scale factor
        
        :return: bitmap image rasterized from svg image
        """        
        filename += EXT_SVG
        path = os.path.join(FOLDER_ICONS, filename)
        cache_path = path + "_" + str(scale)
        
        try:
            i = self.image_cache[cache_path]
            return (cache_path, i)
        except KeyError:
            pass
        
        try:
            svg_image = Parser.parse_file(path)
        except:
            logging.debug("Problem parsing file %s", path)
            return None

        if self.config[USAGE][USE_WEB]:
            try:
                self.svg_cache[cache_path]
            except KeyError:
                t = cache_path.replace('\\','/')
                self.svg_cache[t] = codecs.open(path, "r").read()
        
        return self.scale_svg_image(cache_path, svg_image, bounding_box, scale)
    
    def scale_svg_image(self, cache_path, svg_image, bounding_box=None, scale=1.0):
        """ Load SVG image
        
        :param cache_path: cache key for image
        :param svg_image: bitmap image
        :param bounding_box: image bounding box
        :param scale: scale factor
        
        :return: scaled bitmap image
        """
        w = svg_image.width + 2
        h = svg_image.height + 2
        
        if bounding_box == None:
            bb_w = w * scale
            bb_h = h * scale
        else:
            bb_w = bounding_box.w * scale
            bb_h = bounding_box.h * scale
            
        w_scaled = bb_w / w
        h_scaled = bb_h / h
        scale_factor = min(w_scaled, h_scaled)
        w_final = int(w * scale_factor)
        h_final = int(h * scale_factor)
        
        r = Rasterizer()        
        buff = r.rasterize(svg_image, w_final, h_final, scale_factor)    
        image = pygame.image.frombuffer(buff, (w_final, h_final), 'RGBA')
        
        self.image_cache[cache_path] = image
        
        return (cache_path, image)
    
    def color_to_hex(self, color):
        """ Convert list of color numbers into its hex representation for web
        
        :param color: list of integre numbers
        
        :return: hex representation of the color defined by list of RGB values.
        """
        if not color:
            return None
        return "#%06x" % ((color[0] << 16) + (color[1] << 8) + color[2])
        
    def get_font(self, size):
        """ Return font from cache if not in cache load, place in cache and return.
        
        :param size: font size 
        """
        if os.getcwd() != self.CURRENT_WORKING_DIRECTORY:
            os.chdir(self.CURRENT_WORKING_DIRECTORY)
        
        current_language = self.config[CURRENT][LANGUAGE]
        path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, current_language)
        language_specific_font = None
        for file in os.listdir(path):
            if file.lower().endswith(".ttf"):
                language_specific_font = file
                break
        
        if language_specific_font:
            key = language_specific_font + str(size)
            filename = os.path.join(path, language_specific_font)
        else:
            font_name = self.config[FONT_KEY]
            key = font_name + str(size)
            filename = os.path.join(FOLDER_FONT, font_name)
            
        if key in self.font_cache:
            return self.font_cache[key]
        
        font = pygame.font.Font(filename, size)
        self.font_cache[key] = font
        return font
        
    def scale_image(self, image, ratio):
        """ Scale image using specified ratio
        
        :param ratio: scaling ratio  
              
        :return: scaled image
        """
        if image == None:
            return None
        a = pygame.Surface(ratio, flags=pygame.SRCALPHA)
        if isinstance(image, tuple):
            image = image[1]
        if image:
            pygame.transform.smoothscale(image, ratio, a)
            return a
        else:
            return None
    
    def scale_image_with_padding(self, w, h, img, padding=0, scale_factor=1):
        """ Scale image using specified padding and sacle factor
        
        :param w: image width
        :param h: image height
        :param img: image
        :param padding: padding
        :param scale_factor: scale factor  
               
        :return: scaled image
        """
        w_adjusted = (w - (padding * 2)) * scale_factor
        h_adjusted = (h - (padding * 2)) * scale_factor 
        scale_ratio = self.get_scale_ratio((w_adjusted, h_adjusted), img)
        return self.scale_image(img, scale_ratio)

    def load_radio_playlist(self, language, genre, top_folder):
        """ Load radio playlist

        :param language: laguage for playlist
        :param genre: genre playlist
        :param top_folder: top folder under language
        :return: playlist as a string
        """
        folder = os.path.join(os.getcwd(), FOLDER_LANGUAGES, language, FOLDER_RADIO_STATIONS, top_folder, genre)
        path = os.path.join(folder, FILE_STATIONS)
        playlist =""
        try:
            playlist = codecs.open(path, "r", UTF8).read()
        except Exception as e:
            logging.error(str(e))

        return playlist

    def save_radio_playlist(self, language, genre, playlist):
        """ Save radio playlist

        :param language: laguage for playlist
        :param genre: genre playlist
        :param playlist: playlist as a string to save
        """
        languages = self.config[KEY_LANGUAGES]
        top_folder = ""
        for lang in languages:
            if language == lang[NAME]:
                stations = lang[KEY_STATIONS]
                top_folder = list(stations.keys())[0]

        path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, language, FOLDER_RADIO_STATIONS, top_folder, genre,
            FILE_STATIONS)
        with codecs.open(path, 'w', UTF8) as file:
            file.write(playlist)

    def get_stations_playlist(self, language, genre, stations_per_page):
        """ Load stations for specified language and genre
        
        :param language: the language
        :param genre: the genre
        :param stations_per_page: stations per page used to assign indexes 
               
        :return: list of button state objects. State contains station icons, index, genre, name etc.
        """
        top_folder = self.get_stations_top_folder()
        folder = os.path.join(os.getcwd(), FOLDER_LANGUAGES, language, FOLDER_RADIO_STATIONS, top_folder, genre)
        path = os.path.join(folder, FILE_STATIONS)
        default_icon_path = os.path.join(os.getcwd(), FOLDER_ICONS, FILE_DEFAULT_STATION)
        return self.load_m3u(path, folder, genre, stations_per_page, default_icon_path)
            
    def load_streams(self, streams_per_page):
        """ Load streams
        
        :param streams_per_page: streams per page used to assign indexes 
               
        :return: list of button state objects. State contains icons, index, name etc.
        """
        streams = []
        path = os.path.join(os.getcwd(), FOLDER_STREAMS, FILE_STREAMS)
        default_icon_path = os.path.join(os.getcwd(), FOLDER_ICONS, FILE_DEFAULT_STREAM)
        
        return self.load_m3u(path, FOLDER_STREAMS, "", streams_per_page, default_icon_path)

    def get_streams_string(self):
        """ Read file

        :return: string
        """
        path = os.path.join(os.getcwd(), FOLDER_STREAMS, FILE_STREAMS)
        with codecs.open(path, 'r', UTF8) as file:
            return file.read()

    def save_streams(self, streams):
        """ Save podcasts file

        :param streams: file with podcasts links
        """
        path = os.path.join(os.getcwd(), FOLDER_STREAMS, FILE_STREAMS)
        with codecs.open(path, 'w', UTF8) as file:
            file.write(streams)

    def load_m3u(self, path, folder, top_folder, items_per_page, default_icon_path):
        """ Load m3u playlist
        
        :param path: base path
        :param folder: main folder
        :param top_folder: top folder
        :param items_per_page: items per page
        :param default_icon_path: path to the default icon
        
        :return: list of State objects representing playlist
        """
        items = []
        lines = []
        item_name = None
        index = 0
        
        try:
            lines = codecs.open(path, "r", UTF8).read().split("\n")
        except Exception as e:
            logging.error(str(e))            
        
        for line in lines:
            if len(line.rstrip()) == 0: 
                continue
            
            if line.startswith("#") and not item_name:
                item_name = line[1:].rstrip()
                continue
            
            name = item_name.rstrip()
            path = os.path.join(folder, name + EXT_PNG)
            icon = self.load_image(path)

            if not icon:
                path = os.path.join(folder, name + EXT_JPG)
                icon = self.load_image(path)
            
            if not icon:
                icon = self.load_image(default_icon_path)
            
            state = State()
            state.index = index
            state.genre = top_folder
            state.url = line.rstrip()
            state.name = str(index)
            state.l_name = name
            state.icon_base = icon
            state.comparator_item = NAME
            state.index_in_page = index % items_per_page
            items.append(state)
            index += 1
            item_name = None  
             
        return items
        
    def load_properties(self, path, encoding=None):
        """ Load properties file
        
        :param path: file path
        :param encoding: file encoding  
              
        :return: dictionary with properties
        """
        properties = {}
        file = codecs.open(path, "r", encoding)
        for line in file:
            l = line.rstrip()
            if l and not l.startswith(PROPERTY_COMMENT_CHAR):
                pair = l.split(PROPERTY_SEPARATOR)
                properties[pair[0].strip()] = pair[1].strip()
        return properties
    
    def get_current_language(self):
        """ Get current language parameters
        
        :return: dictionary with current language parameters
        """
        current_language = self.config[CURRENT][LANGUAGE]
        languages = self.config[KEY_LANGUAGES]
        for language in languages:
            if current_language == language[NAME]:
                return language
        return None
    
    def is_radio_enabled(self):
        """ Check that radio mode enabled for current language
        
        :return: True - enabled, False - disabled
        """
        lang = self.get_current_language()
        if lang:
            return lang[RADIO_MODE_ENABLED]
        else:
            return False
    
    def is_audiobooks_enabled(self):
        """ Check that audiobooks mode enabled for current language
        
        :return: True - enabled, False - disabled
        """
        lang = self.get_current_language()
        name = lang[NAME]
        if name == ENGLISH_USA or name == RUSSIAN:
            return True
        
        url = BASE_URL + LANGUAGE_PREFIX + name
        req = request.Request(url)
        try:
            request.urlopen(req)
        except:
            return False

        return True
    
    def get_va_language_commands(self):
        """ Get voice assistant commands for current language
        
        :return: va commands
        """
        current_language = self.get_current_language()
        translations = current_language[TRANSLATIONS]
        va_commands = {}
        for (k, v) in translations.items():
            if "-" in v:
                v = v[:v.find("-")]
            va_commands[k] = v
        return va_commands
    
    def load_languages_menu(self, button_bounding_box):
        """ Load languages menu items
        
        :param button_bounding_box: menu button bounding box
        
        :return: dictionary with menu items
        """
        items = {}
        i = 0
        current_language = self.get_current_language()
        labels = current_language[TRANSLATIONS]
        va_commands = self.get_va_language_commands()
            
        for language in self.config[KEY_LANGUAGES]:
            name = language[NAME]            
            state = State()
            state.name = name
            state.l_name = labels[name]

            path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, name, FILE_FLAG)
            img = self.prepare_flag_image(path, button_bounding_box)
            state.icon_base = (path, img)
            
            state.bgr = self.config[COLORS][COLOR_DARK]
            state.img_x = None
            state.img_y = None
            state.auto_update = True
            state.show_bgr = True
            state.show_img = True
            state.show_label = True
            state.comparator_item = state.name
            state.index = i
            state.voice_commands = va_commands[name]
            state.v_align = V_ALIGN_TOP
            
            items[state.name] = state
            i += 1            
        return items
    
    def prepare_flag_image(self, path, button_bounding_box):
        """ Prepare flag image
        
        :param button_bounding_box: button bounding box
        
        :return: flag image
        """      
        flag = self.load_image(path)
        k = 0.5
        padding = 4
        bb_w = int(button_bounding_box.w * k)
        bb_h = int(button_bounding_box.h * k)           
        scale_ratio = self.get_scale_ratio((bb_w, bb_h), flag[1])
        im = self.scale_image(flag, (scale_ratio[0] - (padding * 2), scale_ratio[1] - (padding * 2)))
        original = im.copy()
        
        img = pygame.Surface((scale_ratio[0], scale_ratio[1]), pygame.SRCALPHA)
        img.blit(im, (padding, padding))
         
        scale = 0.4        
        surf_size = img.get_size()
        scale_size = (int(surf_size[0]*scale), int(surf_size[1]*scale))
        img = pygame.transform.smoothscale(img, scale_size)
        scale_size = (int(surf_size[0]), int(surf_size[1]))
        img = pygame.transform.smoothscale(img, scale_size)
        alpha = 160
        img.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
        img.blit(original, (padding, padding))
 
        return img
    
    def get_stations_top_folder(self):
        """ Get radio stations top folder
        
        :return: top folder name
        """
        language = self.get_current_language()
        stations = language[KEY_STATIONS]
        return list(stations.keys())[0]

    def get_stations_folders(self):
        """ Get radio stations folders
        
        :return: list of folders
        """
        top_folders = None
        language = self.get_current_language()
        try:
            stations = language[KEY_STATIONS]
            top_folder = list(stations.keys())[0]
            top_folders = stations[top_folder]
        except:
            pass
        return top_folders
    
    def get_radio_group_slice(self, group, start, end):
        """ Create radio group slice
        
        :param group: the whole group
        :param start: start index
        :param end: end index
        
        :return: slice list
        """
        keys = list(group.keys())
        key_slice = keys[start : end]
        group_slice = collections.OrderedDict()
        for k in key_slice:
            group_slice[k] = group[k]
            
        return group_slice
            
    
    def load_stations_folders(self, button_bounding_box):
        """ Load languages menu items
        
        :param button_bounding_box: bounding box
        
        :return: dictionary with menu items
        """
        items = collections.OrderedDict()
        i = 0
        current_language = self.config[CURRENT][LANGUAGE]
        folders = self.get_stations_folders()
        top_folder = self.get_stations_top_folder()
            
        for folder in folders:
            name = folder
            path = os.path.join(os.getcwd(), FOLDER_LANGUAGES, current_language, FOLDER_RADIO_STATIONS, top_folder, folder, FILE_FOLDER)
            folder_image = self.load_image(path)
            path_on = os.path.join(os.getcwd(), FOLDER_LANGUAGES, current_language, FOLDER_RADIO_STATIONS, top_folder, folder, FILE_FOLDER_ON)
            folder_image_on = self.load_image(path_on)
            
            state = State()
            state.name = state.l_name = state.genre = name

            if folder_image:
                k = 0.40
                bb_w = int(button_bounding_box.w * k)
                bb_h = int(button_bounding_box.h * k)            
                scale_ratio = self.get_scale_ratio((bb_w, bb_h), folder_image[1])
                scaled_image = self.scale_image(folder_image, scale_ratio)
                state.icon_base = (path, scaled_image)
                if folder_image_on:
                    scaled_image_on = self.scale_image(folder_image_on, scale_ratio)
                    state.icon_selected = (path_on, scaled_image_on)
            
            state.bgr = self.config[COLORS][COLOR_DARK]
            state.img_x = None
            state.img_y = None
            state.auto_update = True
            state.show_bgr = True
            state.show_img = True
            state.show_label = True
            state.comparator_item = state.name
            state.index = i
            state.v_align = V_ALIGN_TOP
            state.v_offset = 35
            state.voice_commands = name
            items[state.name] = state
            i += 1            
        return items
        
    def load_menu(self, names, comparator, disabled_items=None, v_align=None, bb=None, scale=1):
        """ Load menu items
        
        :param names: list of menu item names (should have corresponding filename)
        :param comparator: string used to sort items
        :param disabled_items: list of items which should be disabled
        :param v_align: vertical alignment
        :param bb: bounding box
        :param scale: image scale factor
                
        :return: dictionary with menu items
        """
        items = {}
            
        for i, name in enumerate(names):
            icon = self.load_mono_svg_icon(name, self.COLOR_MAIN, bb, scale)
            icon_on = self.load_mono_svg_icon(name, self.COLOR_ON, bb, scale)
            
            if disabled_items and name in disabled_items:
                icon_off = self.load_mono_svg_icon(name, self.COLOR_OFF, bb, scale)
            else:
                icon_off = None
            
            state = State()
            state.name = name
            state.genre = name
            try: 
                state.l_genre = self.config[LABELS][name]
                state.l_name = self.config[LABELS][name]
            except:
                state.l_genre = name
                state.l_name = name
            state.icon_base = icon
            if icon_on:
                state.icon_selected = icon_on
            else:
                state.icon_selected = icon
                
            if not icon_off:
                state.icon_disabled = icon_on
            else:
                state.icon_disabled = icon_off
                
            state.bgr = self.config[COLORS][COLOR_DARK]
            state.img_x = None
            state.img_y = None
            state.auto_update = True
            state.show_bgr = True
            state.show_img = True
            state.show_label = True
            state.v_align = v_align
            if comparator == NAME:
                state.comparator_item = state.name
            elif comparator == GENRE:
                state.comparator_item = state.genre
            if disabled_items and name in disabled_items:
                state.enabled = False
            state.index = i
            items[state.name] = state
        return items
        
    def get_screensaver_delays(self):
        """ Get screensaver delay button states
        
        :return: dictionary with button states
        """
        names = [KEY_SCREENSAVER_DELAY_1, KEY_SCREENSAVER_DELAY_3, KEY_SCREENSAVER_DELAY_OFF]
        delays = {}
        index = 0
        for n in names:            
            state = State()
            state.name = n
            state.index = index
            state.l_name = self.config[LABELS][n]
            state.comparator_item = index
            state.bgr = self.config[COLORS][COLOR_DARK]
            delays[state.name] = state
            index += 1             
        return delays
        
    def load_screensaver(self, name):
        """ Load screensaver plug-in module and create object
        
        :param name: plug-in name        
        :return: screensaver object
        """
        try:
            s = self.screensaver_cache[name]
            return s
        except KeyError:
            pass
        
        p = PACKAGE_SCREENSAVER + ('.' + name.lower())*2
        m = importlib.import_module(p)
        s = getattr(m, name.title())(self)
        self.screensaver_cache[name] = s
        return s

    def run_script(self, script_name):
        """ Load and run script

        :param script_name: script name
        """
        n = script_name[0:script_name.find(".py")]
        m = importlib.import_module(SCRIPTS + "." + n)
        s = getattr(m, n.title())()

        if s.type == "sync":
            s.start()
        else:
            s.start_thread()

    def get_file_icon(self, file_type, file_image_path=None, icon_bb=None, scale_factor=0.6, url=None):
        """ Load image representing file. Six types of icons supported:
        1. Folder icon
        2. Audio file icon
        3. Image fetched from audio file
        4. Folder with folder icon (folder icon will be displayed in this case)
        5. Playlist icon
        6. CD Drive
        
        :param file_type: defines file type 
        :param file_image_path: path to image file       
        :param icon_bb: image bounding box
        :param scale_factor: scale factor
        :param url: file name
        
        :return: image representing file
        """
        if icon_bb:
            bb = pygame.Rect(0, 0, icon_bb[0], icon_bb[1])
        else:
            bb = None
        
        icon_folder = self.load_mono_svg_icon(ICON_FOLDER, self.COLOR_MAIN, bb, scale_factor)
        icon_file_audio = self.load_mono_svg_icon(ICON_FILE_AUDIO, self.COLOR_MAIN, bb, scale_factor)
        icon_file_playlist = self.load_mono_svg_icon(ICON_FILE_PLAYLIST, self.COLOR_MAIN, bb, scale_factor)
        icon_cd_drive = self.load_mono_svg_icon(ICON_CD_DRIVE, self.COLOR_MAIN, bb, scale_factor)

        scale_ratio = self.config[FOLDER_IMAGE_SCALE_RATIO]
        if icon_bb:
            if self.config[HIDE_FOLDER_NAME]:
                bb = (icon_bb[0], ((icon_bb[1] * (1 / 0.7)) * scale_ratio) - 1)
            else:
                bb = (icon_bb[0] * scale_ratio, icon_bb[1] * scale_ratio)

        if file_type == FOLDER:
            return icon_folder
        elif file_type == FILE_AUDIO:
            img = self.get_image_from_audio_file(url)
            if img:
                ratio = self.get_scale_ratio(bb, img)
                scaled_img = self.scale_image(img, ratio)
                return (url, scaled_img)
            else:
                return icon_file_audio
        elif file_type == FILE_PLAYLIST: return icon_file_playlist
        elif file_type == FILE_CD_DRIVE: return icon_cd_drive
        elif file_type == FOLDER_WITH_ICON or file_type == FILE_IMAGE:
            img = self.load_image(file_image_path, bounding_box=bb)
            if img:
                return img
            else:
                return icon_folder        
   
    def load_folder_content(self, folder_name, rows, cols, bounding_box):
        """ Prepare list of state objects representing folder content
        
        :param folder_name: folder name 
        :param rows: number of rows in file browser  
        :param cols: number of columns in file browser       
        :param bounding_box: file menu bounding box
        
        :return: list of state objects representing folder content
        """
        content = self.file_util.get_folder_content(folder_name)
        if not content:
            return None
        
        items = []
        items_per_page = cols * rows
        item_width = bounding_box.w / cols
        item_height = (bounding_box.h / rows) * 0.7 # as label takes 30 % by default

        for index, s in enumerate(content):
            s.index = index
            s.name = s.file_name
            s.l_name = s.name
            s.icon_base = self.get_file_icon(s.file_type, getattr(s, "file_image_path", ""), (item_width, item_height), url=s.url)
            s.comparator_item = index
            s.bgr = self.config[COLORS][COLOR_DARK]

            if (s.file_type == FOLDER_WITH_ICON or s.file_type == FILE_IMAGE) and self.config[HIDE_FOLDER_NAME]:
                s.show_label = False

            s.show_bgr = True
            s.index_in_page = index % items_per_page
            items.append(s)
        return items

    def load_playlist(self, state, playlist_provider, rows, columns):
        """ Handle playlist
        
        :param state: state object defining playlist
        :param playlist_provider: provider
        :param rows: menu rows 
        :param columns: menu columns
        
        :return: playlist 
        """               
        n = getattr(state, "file_name", None)
        if n == None:
            state.file_name = self.config[FILE_PLAYBACK][FILE_AUDIO]
            
        p = playlist_provider(state)
        
        if not p:
            return

        play_list = []
        
        for i, n in enumerate(p):
            s = State()
            s.index = i
            s.playlist_track_number = i
            s.file_name = n
            s.file_type = FILE_AUDIO
            s.url = state.folder + os.sep + n
            s.playback_mode = FILE_PLAYLIST
            play_list.append(s)
         
        return self.load_playlist_content(play_list, rows, columns)               

    def load_playlist_content(self, playlist, rows, cols):
        """ Prepare list of state objects representing playlist content
        
        :param playlist: list of items in playlist 
        :param rows: number of rows in file browser  
        :param cols: number of columns in file browser 
              
        :return: list of state objects representing playlist
        """
        items = []
        items_per_page = cols * rows

        for index, s in enumerate(playlist):
            s.index = index
            if os.sep in s.file_name:
                s.name = s.l_name = s.file_name[s.file_name.rfind(os.sep) + 1 : ]
            else:
                s.name = s.l_name = s.file_name
            s.icon_base = self.get_file_icon(FILE_AUDIO)
            s.comparator_item = index
            s.bgr = self.config[COLORS][COLOR_DARK]
            s.show_bgr = True
            s.index_in_page = index % items_per_page
            items.append(s)    
        return items

    def get_audio_files_in_folder(self, folder_name):
        """ Return the list of audio files in specified folder
        
        :param folder_name: folder name  
            
        :return: list of audio files
        """
        files = self.file_util.get_folder_content(folder_name)        
        if not files:
            return None
                
        files[:] = (f for f in files if f.file_type == FILE_AUDIO)
        
        for n, f in enumerate(files):
            f.index = n
    
        return files

    def get_audio_file_icon(self, folder, bb, url=None):
        """ Return audio file icon which is album art image. 
        If it's not available then CD image will be returned.
        
        :param folder: folder name 
        :param bb: bounding box  
        :param url: audio file name

        :return: audio file icon
        """
        if url:
            img = self.get_image_from_audio_file(url)
            if img:
                ratio = self.get_scale_ratio((bb.w, bb.h), img)
                scaled_img = self.scale_image(img, ratio)
                return (url, scaled_img)

        d = os.path.join(FOLDER_ICONS, DEFAULT_CD_IMAGE)
        p = self.file_util.get_folder_image_path(folder)
        if not p: p = d
        img = self.load_image(p, False, (bb.w, bb.h))
        return (p, img[1])
    
    def get_cd_album_art(self, album, bb):
        """ Return album art image
        
        :param album: artist name, song name
        :param bb: bounding box 
        
        :return: album art image
        """
        img = url = None
        
        if album != None:
            try:
                url = self.album_art_url_cache[album]
            except:
                url = self.discogs_util.get_album_art_url(album)
                if url != None:
                    self.album_art_url_cache[album] = url
        
        if url == None:
            d = os.path.join(FOLDER_ICONS, DEFAULT_CD_IMAGE)
            img = self.load_image(d)
            url = d
        else:
            try:
                i = self.image_cache[url]
                return (url, i)
            except KeyError:
                pass
            img = self.load_image_from_url(url)
        
        ratio = self.get_scale_ratio((bb.w, bb.h), img[1])
        if ratio[0] % 2 != 0:
            ratio = (ratio[0] - 1, ratio[1])
        if ratio[1] % 2 != 0:
            ratio = (ratio[0], ratio[1] - 1)   
        img = self.scale_image(img, ratio)
        
        if url != None:
            self.image_cache[url] = img
        
        return (url, img)

    def get_dictionary_value(self, d, key, df=None):
        """ Return value retrieved from provided dictionary by provided key
        
        :param d: dictionary
        :param key: key
        :param df: default value
        """
        if not d or not key: return None
        
        try:
            return d[key]
        except:
            return df 

    def load_image_from_url(self, url, header=False):
        """ Load image from specified URL
        
        :param url: image url
        
        :return: image from url
        """
        try:
            if header == False:
                stream = urlopen(url).read()
            else:
                hdrs = {'User-Agent': 'PeppyPlayer +https://github.com/project-owner/Peppy'}
                req = request.Request(url, headers=hdrs)
                stream = urlopen(req).read()

            buf = BytesIO(stream)
            image = pygame.image.load(buf).convert_alpha()
            return (url, image)
        except Exception as e:
            logging.debug(e)
            return None
        
    def get_hash(self, s):
        """ Return string's hash
        
        :param s: input string
        
        :return: hash of the input string
        """
        m = hashlib.sha1()
        m.update(s)
        return m.hexdigest() 
 
    def load_menu_screen_image(self, url, w, h):
        """ Load image
        
        :param url: image url
        :param w: image width
        :param h: image height
        
        :return: hash of the input string
        """
        img_scaled = None
        img = self.load_image_from_url(url)
        image_padding = 4 
        if img:
            img_scaled = self.scale_image_with_padding(w, h, img[1], image_padding, 1.0)                
        
        if not img_scaled:
            return None
        else:
            return img_scaled
        
    def is_screensaver_available(self):
        """ Check that at least one screensaver available
        
        :return: True - available, False - unavailable
        """
        s = self.config[SCREENSAVER_MENU]
        n = 0
        
        for v in s.values():
            if v == True:
                n = 1
                break
            
        if n > 0:
            return True
        else:
            return False
        
    def encode_url(self, url):
        """ Encode URL using ascii encoding. If doesn't work use UTF-8 encoding
        
        :param url: input URL
        :return: encoded URL
        """        
        try:
            url.encode('ascii')
            url = url.replace(" ", "%20")
            url = url.replace("_", "%5F")
            return url
        except:
            pass
        
        new_url = url.encode('utf-8')
        new_url = urllib.parse.quote(new_url)
        new_url = new_url.replace("%22", "\"")
        new_url = new_url.replace("%3A", ":")
        new_url = new_url.replace("%25", "%")
        
        return new_url
    
    def set_equalizer(self, values):
        """ Set equalizer values for all frequency bands
        
        :param values: values in range 0-100
        """
        for i, v in enumerate(values):
            self.set_equalizer_band_value(i + 1, v)

    def set_equalizer_band_value(self, band, value):
        """ Set equalizer values for one frequency bands
        
        :param band: frequency band number in range 1-10
        :param value: value in range 0-100
        """
        command = "echo cset numid={0} {1} | amixer -D equal -s".format(band, value)
        if self.config[LINUX_PLATFORM]:
            try:
                Popen(command, shell=True)
            except Exception as e:
                logging.debug(e)
        
    def read_storage(self):
        """ Read storage """
        
        b64 = ZipFile("storage", "r").open("storage.txt").readline()
        storage = base64.b64decode(b64)[::-1].decode("utf-8")[2:182]
        n1 = 40
        n2 = 32
        n3 = 8
        n4 = 60
        n5 = 40
        self.k1 = storage[:n1]
        self.k2 = storage[n1 : n1 + n2]
        self.k3 = storage[n1 + n2 : n1 + n2 + n3]
        self.k4 = storage[n1 + n2 + n3 : n1 + n2 + n3 + n4]
        self.k5 = storage[n1 + n2 + n3 + n4 : n1 + n2 + n3 + n4 + n5]
        
    def get_flipclock_digits(self, bb):
        """ Get digits for the flip clock
        
        :param bb: digit image bounding box
        
        :return: list of digit images
        """
        digits = []
        
        for n in map(str, range(10)):
            filename = n + EXT_PNG
            path = os.path.join(FOLDER_ICONS, filename)
            t = path.replace('\\','/')
            image = self.load_image(t)
            r = self.get_scale_ratio((bb.w/4, bb.h), image[1], True)
            i = self.scale_image(image, r)
            digits.append((path, i))
            
        return digits
    
    def get_flipclock_separator(self, height):
        """ Get image for flip clock separator/colon
        
        :param height: image height
        
        :return: separator image
        """
        path = os.path.join(FOLDER_ICONS, FILE_COLON)
        t = path.replace('\\','/')
        image = self.load_image(t)
        r = self.get_scale_ratio((height, height), image[1], True)
        i = self.scale_image(image, r)
        return (path, i)

    def get_flipclock_key(self, image_name, height):
        """ Get key image for flip clock 
        
        :param image_name: image name
        :param height: image height
        
        :return: key image
        """
        path = os.path.join(FOLDER_ICONS, image_name)
        t = path.replace('\\','/')
        image = self.load_image(t)
        s = image[1].get_size()
        h = height / 7.05
        k = h / s[1]
        w = s[0] * k
        r = self.get_scale_ratio((w, h), image[1], True)
        i = self.scale_image(image, r)
        return (path, i)

    def get_podcasts_util(self):
        """ Get podcasts util object

        :return: podcasts util object
        """
        if self.podcasts_util == None:
            from util.podcastsutil import PodcastsUtil
            self.podcasts_util = PodcastsUtil(self)
        return self.podcasts_util
