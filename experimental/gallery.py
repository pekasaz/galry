"""Display all images in a directory."""

import Image
import numpy as np
import os
import sys
from galry import *
from qtools import inthread, inprocess

# load an image
def load(file, size=None):
    img = Image.open(file)
    if size is not None:
        img.thumbnail((size, size))
    return np.array(img)

def get_aspect_ratio(image):
    hi, wi, _ = image.shape
    return float(wi) / hi


class Loader(object):
    def load(self, key, path):
        print "loading", key, path[-8:]
        img = load(path, 1366)
        return img
        
    @staticmethod
    def load_done(key=None, path=None, _result=None):
        CACHE[key] = _result


class Navigator(object):
    def __init__(self, n, steps):
        self.n = n
        self.steps = steps
        self.i = 0
        self.dir = 0
    
    def set(self, i):
        self.i = i
        self.dir = 0
    
    def next(self):
        if self.i < self.n - 1:
            self.i += 1
        self.dir = 1
        
    def previous(self):
        if self.i > 0:
            self.i -= 1
        self.dir = -1
    
    def current(self):
        return self.i
    
    def indices(self):
        steps = self.steps
        before = range(max(0, self.i - steps), self.i)
        after = range(self.i + 1, min(self.n - 1, self.i + steps) + 1)
        current = [self.i]
        if dir >= 0:
            return current + after + before
        else:
            return current + before + after
        
    
class PictureViewer(object):
    EMPTY = np.zeros((2, 2, 3))
    
    def __init__(self, folder=None):
        # get list of images in the folder
        if len(sys.argv) > 1:
            folder = sys.argv[1]
        else:
            folder = '.'
        self.folder = folder
        self.files = sorted(filter(lambda f: f.lower().endswith('.jpg'), os.listdir(folder)))
        self.cache = {}
        self.n = len(self.files)
        # Number of images to keep forward/backward in cache.
        self.steps = 2
        self.loader = inprocess(Loader)()
        self.nav = Navigator(self.n, self.steps)
        self.set_index(0)
        
    def set_index(self, i):
        self.nav.set(i)
        indices = self.nav.indices()
        paths = [(j, os.path.join(self.folder, self.files[j])) for j in indices 
            if j not in self.cache]# or self.cache[j] is None]
        # Tag keys that are being loaded so that they're not loaded once again.
        for j in indices:
            if j not in self.cache:
                self.cache[j] = None
        [self.loader.load(j, path) for j, path in paths]
    
    def next(self):
        self.nav.next()
        self.set_index(self.nav.current())
    
    def previous(self):
        self.nav.previous()
        self.set_index(self.nav.current())
    
    def current(self):
        return self[self.nav.current()]
    
    def __getitem__(self, key):
        img = self.cache.get(key, None)
        return img
        # if img is None:
            # return self.EMPTY
        # else:
            # return img
        
    def __setitem__(self, key, value):
        self.cache[key] = value
        

def show_image(figure, img):
    if img is None:
        return
    ar = get_aspect_ratio(img)
    figure.set_data(texture=img)
    figure.set_rendering_options(constrain_ratio=ar)
    figure.resizeGL(*figure.size)

def next(fig, params):
    pw.next()
    global CURRENT_IMAGE
    CURRENT_IMAGE = pw.current()
    show_image(fig, CURRENT_IMAGE)
    
def previous(fig, params):
    pw.previous()
    global CURRENT_IMAGE
    CURRENT_IMAGE = pw.current()
    show_image(fig, CURRENT_IMAGE)

def anim(fig, (t,)):
    global CURRENT_IMAGE
    image_last_loaded = pw.current()
    # Skip if current image in memory is None.
    if image_last_loaded is None or np.array_equal(image_last_loaded, pw.EMPTY):
        return
    # Update only if current displayed image is empty, and current image in
    # memory is not empty.
    if (CURRENT_IMAGE is None or np.array_equal(CURRENT_IMAGE, pw.EMPTY)):
        print "update"
        CURRENT_IMAGE = pw.current()
        show_image(fig, CURRENT_IMAGE)


if __name__ == '__main__':

    pw = PictureViewer()
    CACHE = pw.cache
    CURRENT_IMAGE = pw.EMPTY
        
    # create a figure and show the filtered image    
    figure(constrain_ratio=1, constrain_navigation=True, toolbar=False)
    imshow(np.zeros((2,2,3)), points=(-1., -1., 1., 1.), 
                mipmap=False,
                minfilter='LINEAR',
                magfilter='LINEAR')

    # previous/next images with keyboard
    action('KeyPress', previous, key='Left')
    action('KeyPress', next, key='Right')
    animate(anim, dt=.01)


    show()


    pw.loader.join()
