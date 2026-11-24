"""In-process Launchpad substitute; never opens MIDI or sends hardware LEDs."""
class DemoLaunchpad:
    def __init__(self):
        self.leds = {}

    def LedCtrlXYByRGB(self, x, y, colour):
        self.leds[x, y] = tuple(colour)

    def LedCtrlXYByCode(self, x, y, colour):
        self.leds[x, y] = colour

    def LedCtrlPulseXYByCode(self, x, y, colour):
        self.leds[x, y] = ('pulse', colour)

    def LedCtrlFlashXYByCode(self, x, y, colour):
        self.leds[x, y] = ('flash', colour)

    def Close(self):
        self.leds.clear()
