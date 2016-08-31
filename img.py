import wx


class AppImages():
    def __init__(self, path):
        self.path = path
        self.img_dict = {'update': 'gnome-fs-bookmark-16.png',
                         'quit': 'stock_exit-16.png',
                         'help': 'stock_help-16.png',
                         'toilet': 'stock_toilet-paper.png',
                         'upgrade': 'stock_update-data-16.png',
                         'log': 'stock_task-16.png',
                         'cancel': 'stock_cancel-16.png'}

    def get(self, iconname):
        try:
            image = 'img\\' + self.img_dict[iconname]
        except KeyError:
            print 'Image: "{}" not found!'.format(iconname)
            image = 'img\\' + self.img_dict['toilet']
        wximage = wx.Image(self.path + image, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        return wximage
