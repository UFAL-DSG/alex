class PlatformInfo(object):
    def __init__(self, from_stop, to_stop, from_city, to_city, train_name):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.from_city = from_city
        self.to_city = to_city
        self.train_name = train_name

    def __unicode__(self):
        return u"%s, %s -- %s, %s" % (self.from_stop, self.from_city,
                                     self.to_stop, self.to_city, )


class PlatformFinderResult(object):
    def __init__(self, platform, track, direction):
        self.platform = platform
        self.track = track
        self.direction = direction

    def __unicode__(self):
        return u"PlatformFinderResult(platform=%s, track=%s, direction=%s)" % (
            unicode(self.platform),
            unicode(self.track),
            unicode(self.direction), )


class CRWSPlatformFinder(object):
    def __init__(self, crws_response):
        self.crws_response = crws_response

    def _matches(self, crws_stop, stop):
        #alex_stop = self.fn_idos_to_alex_stop(crws_stop)
        res = crws_stop == stop
        print res, crws_stop, stop


        return res

    def find_platform_by_station(self, to_obj):
        def norm(x):
            return x.upper()
        names = set(norm(obj._sName) for obj in to_obj[0])
        for entry in self.crws_response.aoRecords:
            # Figure out whether this entry corresponds to the entry the user
            # is interested in.
            matched_obj = None
            dst_matches = norm(entry._sDestination) in names
            dir_matches = False
            if dst_matches:
                matched_obj = entry._sDestination
            else:
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


