# -*- mode: python -*-

base_path = os.path.abspath(SPECPATH)

myicon = base_path + os.sep + 'icon.ico'
myversion = base_path + os.sep + 'version.txt'

def addTranslations():
    lng_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(base_path + os.sep + 'locale')) for f in fn if f.endswith('.mo')]
    extraDatas = []
    for src_path in lng_files:
        extraDatas.append((src_path.replace(base_path + os.sep, ''), src_path, ''))
    return extraDatas

def addImages():
    img_path = base_path + os.sep + "img" + os.sep
    extraDatas = []
    for file in os.listdir(img_path):
        extraDatas.append(('img\\' + file, img_path + file, ''))
    return extraDatas

block_cipher = None

a = Analysis(['WPKG-GP-Client.py'],
             pathex=[base_path],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)

# Add data to dist
a.datas += addImages()
a.datas += addTranslations()
a.datas += [('wpkg-gp_client_example.ini', base_path + os.sep + 'wpkg-gp_client_example.ini', ''),
            ('help.html', base_path + os.sep + 'help.html', '')]


pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='WPKG-GP-Client',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon=myicon,
          version=myversion
          )
		  
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='WPKG-GP-Client')
