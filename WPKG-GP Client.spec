# -*- mode: python -*-

block_cipher = None


a = Analysis(['WPKG-GP-Client.py'],
             pathex=['D:\\PY\\WPKG-GP-Client'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
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
          icon='icon.ico',
          version='version.txt'
          )
		  
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='WPKG-GP-Client')
