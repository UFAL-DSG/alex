# encoding: utf8
import re


class PlatformInfo(object):
    def __init__(self, from_stop, to_stop, from_city, to_city, train_name, directions):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.from_city = from_city
        self.to_city = to_city
        self.train_name = train_name
        self.directions = directions

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


class CRWSPlatformInfo(object):
    station_name_splitter = re.compile(r'(\W*)', re.UNICODE)

    def __init__(self, crws_response, finder):
        self.crws_response = crws_response
        self.finder = finder

    def _matches(self, crws_stop, stop):
        crws_stop = crws_stop.lower()
        stop = stop.lower()

        crws_stop_parts = self.station_name_splitter.split(crws_stop)
        stop_parts = self.station_name_splitter.split(stop)

        if len(crws_stop_parts) != len(stop_parts):
            if len(crws_stop_parts) > len(stop_parts):
                longer = crws_stop_parts
                shorter = stop_parts
            else:
                longer = stop_parts
                shorter = crws_stop_parts

            # If the longer is longer only because of abbreviation punctuation ('.') it will be longer by 2.
            if len(longer) != len(shorter) + 2 or longer[-1] != '':
                return False
            else:
                shorter.append('')
                longer.pop()

        return self._do_parts_match(crws_stop_parts, stop_parts)

    def _do_parts_match(self, crws_stop_parts, stop_parts):
        for p1, p1next, p2, p2next in zip(crws_stop_parts, crws_stop_parts[1:] + [''], stop_parts,
                                          stop_parts[1:] + ['']):
            if p1 == p2:
                continue
            elif p1.startswith(p2) and p2next.startswith('.'):
                continue
            elif p2.startswith(p1) and p1next.startswith('.'):
                continue
            elif p1.replace('.', '').strip() == p2.replace('.', '').strip():
                # It's okay if the parts are just whitespaces or whitespaces and periods.
                continue
            else:
                return False
        return True

    def _normalize_name(self, name):
        if name:
            res = ""
            last_was_alpha = None
            for i in name:
                curr_is_alpha = i.isalpha()
                if not last_was_alpha == curr_is_alpha and last_was_alpha is \
                        not None:
                    res += " "
                last_was_alpha = curr_is_alpha
                res += i

            return res
        else:
            return name

    def find_platform_by_station(self, to_obj):
        def norm(x):
            return x.upper()

        names = set(norm(obj._sName) for obj in to_obj[0])
        for entry in self.crws_response.aoRecords:
            # Figure out whether this entry corresponds to the entry the user
            # is interested in.
            dst_matches = False
            matched_obj = None
            for n in names:
                if self._matches(entry._sDestination, n):
                    dst_matches = True
                    break

            dir_matches = False

            if dst_matches:
                matched_obj = entry._sDestination
            else:
                for dir in getattr(entry, 'asDirection', []):
                    for n in names:
                        if self._matches(n, dir):
                            dir_matches = True
                            matched_obj = dir
                            break
                    else:
                        continue
                    break

            if dst_matches or dir_matches:
                platform = getattr(entry, '_sStand', None)
                track = getattr(entry, '_sTrack', None)

                platform = self._normalize_name(platform)
                track = self._normalize_name(track)
                matched_obj = self.finder.get_stop_full_name(matched_obj)

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
