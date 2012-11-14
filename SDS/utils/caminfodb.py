from SDS.utils.parsers import CamTxtParser

class CamInfoDb(object):
    def __init__(self, db_path):
        ctp = CamTxtParser()
        self.data = ctp.parse(db_path)

    def matches(self, rec, query):
        for key, value in query.items():
            if not rec.get(key) == value:
                return False

        return True

    def get_matching(self, query):
        res = []
        for rec in self.data:
            if self.matches(rec, query):
                res += [rec]

        return res


