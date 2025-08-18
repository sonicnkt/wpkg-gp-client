import wx
from os.path import join


class AppImages:
    def __init__(self, path):
        # Initialize the AppImages object with the base path for image files
        self.path = path
        # Dictionary mapping icon names to image filenames
        self.img_dict = {
            'update': 'gnome-fs-bookmark-16.png',
            'quit': 'stock_exit-16.png',
            'help': 'stock_help-16.png',
            'toilet': 'stock_toilet-paper.png',  # Placeholder/fallback image
            'upgrade': 'stock_update-data-16.png',
            'log': 'stock_task-16.png',
            'cancel': 'stock_cancel-16.png'
        }

    def get(self, iconname):
        """
        Returns a wx.Bitmap image object for the given icon name.
        If the icon name is unknown, a fallback placeholder image is used.
        """
        try:
            # Attempt to retrieve the filename for the requested icon
            image = join(self.path, 'img', self.img_dict[iconname])
        except KeyError:
            # Icon name not found: notify the user and use the fallback image
            print(f'Image: "{iconname}" not found! Using placeholder image.')
            image = join(self.path, 'img', self.img_dict['toilet'])
        # Load the image from disk and convert it to a wx.Bitmap for use in wxPython
        wximage = wx.Image(image, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        return wximage
