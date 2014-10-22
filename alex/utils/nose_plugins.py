from nose2.events import Plugin

class AppSkipperPlugin(Plugin):
    
    configSection = 'appskipper'
    commandLineSwitch = ('S', 'skip-app', 'Skip tests for applications - especially the ones with third party dependencies')

    def __init__(self):
        pass
