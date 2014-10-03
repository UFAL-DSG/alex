class PlatformInfo(object):
    def __init__(self, from_station, to_station, train_name):
        self.from_station = from_station
        self.to_station = to_station
        self.train_name = train_name


class PlatformFinderResult(object):
    def __init__(self, platform, track, direction):
        self.platform = platform
        self.track = track
        self.direction = direction

    def __unicode__(self):
        return "PlatformFinderResult(platform=%s, track=%s, direction=%s)" % (
            str(self.platform), str(self.track), str(self.direction), )


class CRWSPlatformFinder(object):
    def __init__(self, crws_response):
        self.crws_response = crws_response

    def _matches(self, crws_stop, stop):
        #alex_stop = self.fn_idos_to_alex_stop(crws_stop)
        res = crws_stop == stop
        print res, crws_stop, stop


        return res

    def find_platform_by_station(self, to_obj):
        names = set(obj._sName for obj in to_obj[0])
        for entry in self.crws_response.aoRecords:
            # Figure out whether this entry corresponds to the entry the user
            # is interested in.
            matched_obj = None
            dst_matches = entry._sDestination in names
            if dst_matches:
                matched_obj = entry._sDestination
            else:
                dir_matches = False
                for dir in getattr(entry, 'asDirection', []):
                    if dir in names:
                        dir_matches = True
                        matched_obj = dir
                        break

            if dst_matches or dir_matches:
                platform = getattr(entry, '_sStand', None)
                track = getattr(entry, '_sTrack', None)


                return PlatformFinderResult(platform, track, matched_obj)

        return None

    def find_platform_by_train_name(self, train_name):
        for entry in self.crws_response.aoRecords:
            # Figure out whether this entry corresponds to the entry the user
            # is interested in.
            if entry.oInfo._sNum2.lower().startswith(train_name.lower()):
                platform = getattr(entry, '_sStand', None)
                track = getattr(entry, '_sTrack', None)

                return PlatformFinderResult(platform, track, train_name)

        return None


