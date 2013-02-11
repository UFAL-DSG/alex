import re
import sys
from collections import defaultdict

class CamTxtParser(object):
    """Parser of files of the following format:
    <<BOF>>
    [record]

    [record]

    ...
    <<EOF>>

    where [record] has the following format:

    <<[record]>>
    [property name]([property value])
    <</[record]>>

    [property name] and [property value] are arbitrary strings

    Any " or ' characters are stripped from the beginning and end
    of each [property value]."""

    line_expr = re.compile(r"^(?P<name>[^\s]*)\((?P<value>.*)\)$")

    def __init__(self, lower=False):
        self.lower = lower

    def parse(self, f_obj):
        """Parse the given file and return list of dictionaries with parsed values.

        Arguments:
        f_obj -- filename of file or file object to be parsed"""

        if type(f_obj) is str:
            f_obj = open(f_obj, 'r+b')

        assert type(f_obj) is file

        objs = []
        n_obj = defaultdict(lambda: [])
        blank = True

        for ln in f_obj:
            if self.lower:
                ln = ln.lower()
            ln = ln.strip()
            if len(ln) == 0 and not blank:
                objs += [n_obj]
                n_obj = defaultdict(lambda: [])
                blank = True

            m_obj = self.line_expr.match(ln)
            if m_obj is not None:
                blank = False

                try:
                    key, value = m_obj.groups()
                    value = value.strip('"').strip("'")
                    n_obj[key] += [value]
                except ValueError:
                    print >>sys.stderr, 'ignoring', m_obj.groups()

        return objs


if __name__ == '__main__':
    print CamTxtParser().parse("/xdisk/devel/vystadial/alex//applications/CamInfoRest/cued_data/CIRdbase_V7.txt")
