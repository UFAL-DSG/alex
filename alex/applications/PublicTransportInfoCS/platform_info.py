class PlatformInfo(object):
    def __init__(self, from_city, to_city):
        self.from_city = from_city
        self.to_city = to_city


class PlatformFinderResult(object):
    def __init__(self, platform, track):
        self.platform = platform
        self.track = track

    def __unicode__(self):
        return "PlatformFinderResult(platform=%s, track=%s)" % (
            str(self.platform), str(self.track), )


class CRWSPlatformFinder(object):
    def __init__(self, crws_response):
        self.crws_response = crws_response

    def _matches(self, crws_stop, stop):
        res = crws_stop.lower().startswith(stop.lower())
        print res, crws_stop, stop

        return res

    def find_platform(self, platform_info):
        for entry in self.crws_response.aoRecords:
            # Figure out whether this entry corresponds to the entry the user
            # is interested in.
            dst_matches = self._matches(entry._sDestination,
                                        platform_info.to_city)

            dir_matches = False
            for dir in getattr(entry, 'asDirection', []):
                if self._matches(dir, platform_info.to_city):
                    dir_matches = True
                    break

            if dst_matches or dir_matches:
                platform = getattr(entry, '_sStand', None)
                track = getattr(entry, '_sTrack', None)

                return PlatformFinderResult(platform, track)

        return None



