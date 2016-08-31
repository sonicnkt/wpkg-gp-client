import wx
import wx.html
import webbrowser
import markdown2

class HelpDialog(wx.Dialog):
    def __init__(self, helpFile, title='Temp'):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=title)

        self.help = helpFile
        self.InitUI()
        self.SetSize((600, 600))

    def InitUI(self):

        self.panel = wx.Panel(self, wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.html = help = wx.html.HtmlWindow(self.panel, -1, style=wx.NO_BORDER)
        # Bind LINK Click Event to own Function
        help.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.OnLinkClicked)
        # http://wxpython-users.1045709.n5.nabble.com/Open-a-URL-with-the-default-browser-from-an-HtmlWindow-td2326349.html
        #import codecs
        #file = codecs.open(self.help, "r", "utf-8")
        file = open(self.help, "r")
        test = file.read().decode("utf-8")
        html = markdown2.markdown(test, extras=["tables"])
        html = '<body bgcolor="#f0f0f5">' + html
        #print html
        help.SetPage(html)
        sizer.Add(help, 1, wx.EXPAND)
        self.panel.SetSizerAndFit(sizer)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnLinkClicked(self, link):
        # If Link is an anchor link let the html window do its job
        # If it is not an anchor link let the default browser open the page
        href = link.GetLinkInfo().GetHref()
        anchor = href[1:]
        if href.startswith('#'):
            self.html.ScrollToAnchor(anchor)
        else:
            wx.BeginBusyCursor()
            webbrowser.open(href)
            wx.EndBusyCursor()

    def OnClose(self, e):
        self.Destroy()

class MyApp(wx.App):
    def OnInit(self):
        frame = HelpDialog('help.md', title='WPKG-GP-Client - Help')
        frame.Show(True)
        return True

if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()