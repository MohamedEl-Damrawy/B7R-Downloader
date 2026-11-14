[app]

# title of your application
title = Velo Downloader

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = main.py

# directory where the executable output is generated
exec_directory = .

# path to the project file relative to project_dir
project_file = 

# application icon
icon = C:\Users\moham\AppData\Local\Programs\Python\Python312\Lib\site-packages\PySide6\scripts\deploy_lib\pyside_icon.ico

[python]

# python packages to install
packages = Nuitka==4.1.1

# buildozer = for deploying Android application
android_packages = buildozer==1.6.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
qml_files = 

# excluded qml plugin binaries
excluded_qml_plugins = 

# qt modules used. comma separated
modules = Core,Gui,Network,Widgets

# qt plugins used by the application. only relevant for desktop deployment
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,networkaccess,networkinformation,platforminputcontexts,platforms,platformthemes,styles,tls

[android]

wheel_pyside = 
wheel_shiboken = 
plugins = 

[ios]

wheel_pyside = 
wheel_shiboken = 
xcframework_path = 
bundle_id = 
team_id = 
version = 1.0
deployment_target = 
entitlements = 
signing_style = Automatic
header_search_paths = 

[nuitka]

macos.permissions = 

# mode of using nuitka. accepts standalone or onefile. default = standalone
mode = standalone

# include app data/resources and bundled binaries/licenses
extra_args = --quiet --noinclude-qt-translations --include-data-dir=resources=resources --include-data-dir=vendor=vendor --include-data-dir=licenses=licenses --include-data-files=LICENSE=LICENSE --windows-console-mode=disable --company-name=Mohamed El-Damrawy (Individual) --product-name=Velo Downloader --file-version=0.1.0.0 --product-version=0.1.0.0 --file-description=Velo Downloader --copyright=Copyright (c) 2026 Mohamed El-Damrawy

[buildozer]

mode = debug
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 
