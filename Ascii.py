#!/usr/bin/env python

import os
import sys, getopt
from PIL import Image, ImageFont, ImageDraw, ImageOps

# default font to be used for ascii rendering
c_default_font = "./data/DejaVuSansMono.ttf"

class Ascii:
    """
    Create an ascii mosaic of a given image
    """
    def __init__(self, in_path, out_path=None, font_size=20):
        """
        initialize
        :param in_path: path to original image
        :param out_path: output path, may be None to use current directory (out_path/<original image name>_result.jpg)
        :param font_size: desired font size in output image (not output text file)
        """
        if os.path.exists(in_path):
            self.in_path = in_path
        else:
            print('error: cannot open file')
            exit(-1)

        if out_path is not None and os.path.exists(out_path):
            self.out_path = os.path.join(out_path, self.in_path.split('/')[-1].split('.')[0] + '_result')
        else:
            self.out_path = os.path.join('./', self.in_path.split('/')[-1].split('.')[0] + '_result')

        # x = y = font_size, because we need quadratic
        self.x = self.y = self.font_size = font_size
        self.font = ImageFont.truetype(c_default_font, self.font_size)
        self.helper = AsciiHelper(font=self.font)  # font size here is irrelevant, since imgs are not used for anything

    def create_ascii_file(self):
        """ crate a text file containing an ascii representation of a given image """
        # get original image
        img = Image.open(self.in_path)
        w, h = img.size
        filename = self.out_path + '.txt'
        file = open(filename, 'w')

        # create ascii && image brightness list
        ascii_list = self.helper.create_ascii_list()
        image_list = self.scan_image_pixels()

        # find brightness matches
        match_list = self.find_ascii_match(ascii_list, image_list, w)

        # write match list to file line per line
        for i in range(0, h):
            for j in range(0, w):
                file.write(chr(int(match_list[(w * i) + j])))
            file.write('\n')
        file.close()
        print("ascii text file created")

    def create_ascii_image(self):
        """ Create an ascii image representation of a given image """
        # get original image
        img = Image.open(self.in_path)
        w, h = img.size

        # find brightness matches
        match_list = self.get_match_list()

        # create output image
        out = Image.new('L', (w * self.x, h * self.y), 255)

        for i in range(0, h):
            for j in range(0, w):
                ascii_img = self.get_text_image(chr(int(match_list[(w * i) + j])))
                out.paste(ascii_img, (j * self.x, i * self.y))

        filename = self.out_path + '.jpg'
        out.save(os.path.join(filename))
        print("ascii image created")

    def get_match_list(self):
        """ return a list of ascii values that match brightness of the respective pixel in image"""
        # get original image
        img = Image.open(self.in_path)
        w, h = img.size

        # create ascii && image brightness list
        ascii_list = self.helper.create_ascii_list()
        image_list = self.scan_image_pixels()

        # find brightness matches
        return self.find_ascii_match(ascii_list, image_list, w)

    def scan_image_pixels(self):
        """ scan an images brightness pixel per pixel && return list """
        img = ImageOps.grayscale(Image.open(self.in_path))
        return list(img.getdata())

    def find_ascii_match(self, ascii_list, image_list, w):
        """
        compare pixel values of an image to brightness list values and return a list of keys
        scale of ascii symbol to pixel is 2:1, so compare 2 rows at once
        for simplicity's sake, scan the last one or two rows separately
        """
        match_list = []
        for i in range(len(image_list)):
            if len(image_list) > (i + w):
                val = (image_list[i] + image_list[i + w]) / 2
            else:
                val = image_list[i]
            for file, bri in ascii_list:
                if val <= bri:
                    match_list.append(file.split('.')[0])
                    break
            if ((i % w) == 0) and (len(image_list) > (i + w)):
                i += w
        return match_list

    def get_text_image(self, text):
        """ write the given text to an image and return """
        img = Image.new('L', (self.x, self.y), 255)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), text, font=self.font)
        return img


class AsciiHelper:
    def __init__(self, path='./images', font=None, font_size=20):
        """
        Initialize
        :param path: folder to store ascii symbol images
        :param font: a preexisting ImageFont, or None to get default
        :param font_size: [only applicable if font=None] font size for default font
        """
        self.path = path
        self.font_size = font_size
        if font is None:
            self.font = ImageFont.truetype(c_default_font, self.font_size)
        else:
            self.font = font
        self.ascii_list = self.create_ascii_list()

    def create_ascii_list(self, reverse_sort=False):
        """
        create a list containing brightness values of ascii symbols
        :param reverse_sort: sort list from highest to lowest
        :return: a sorted list of ascii symbol brightness values
        """
        b_list = self.scan_ascii_images(self.get_ascii_images())
        b_list.sort(key=lambda tup: tup[1], reverse=reverse_sort)
        return b_list

    def get_ascii_images(self):
        """
        create an image for each ascii symbol and save to self.path
        :return: nothing
        """
        # create images of ascii symbols
        # create image for null separately (because 1-31 are blank symbols && not needed)
        ascii_list = [(str(0), self.get_ascii_image(chr(0)))]
        for i in range(32, 128):
            ascii_list.append((str(i), self.get_ascii_image(chr(i))))
        return ascii_list

    def get_ascii_image(self, symbol):
        """
        return a given symbol as an image
        :param symbol: an ascii character
        :return: a list of tuples (ascii key, image)
        """
        img = Image.new('L', ((self.font.size // 2), self.font.size), 255)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), symbol, font=self.font)
        return img

    def scan_ascii_images(self, ascii_list):
        """
        scan all images in a folder && return a list of brightness values
        :return: a map of symbol name and brightness
        """
        b_map = []
        for key, img in ascii_list:
            score = calculate_brightness(img) * 255
            b_map.append((key, score))
        return b_map


def calculate_brightness(image):
    """ from: https://gist.github.com/kmohrf/8d4653536aaa88965a69a06b81bcb022 """
    grayscale_image = image.convert('L')
    histogram = grayscale_image.histogram()
    pixels = sum(histogram)
    brightness = scale = len(histogram)

    for index in range(0, scale):
        ratio = histogram[index] / pixels
        brightness += ratio * (-scale + index)

    return 1 if brightness == 255 else brightness / scale


def main(argv):
    # parse command line
    src = ''
    dst = ''
    help_str = 'Ascii.py -i sourceImage -o outputDirectory'

    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["input=", "output="])
    except getopt.GetoptError:
        print(help_str)
        sys.exit(1)
    for opt, arg in opts:
        if opt == '-h':
            print(help_str)
            sys.exit(0)
        elif opt in ("-i", '--input'):
            src = arg
        elif opt in ("-o", "--output"):
            dst = arg
        else:
            print("unrecognized parameter: " + opt)
    if src == '':
        print("need at least a source image");
        print(help_str)
        sys.exit(1)

    ascii = Ascii(src, dst if dst != '' else None)
    print("asciification of %s in progress" % (src))
    ascii.create_ascii_file()
    ascii.create_ascii_image()

if __name__ == '__main__':
    main(sys.argv[1:])
