from SDS.utils.parsers import CamTxtParser

class CamInfoDb(object):
    def __init__(self, db_path):
        ctp = CamTxtParser(lower=True)
        self.data = ctp.parse(db_path)

    def matches(self, rec, query):
        for key, value in query.items():
            if not rec.get(key) == value:
                return False

        return True

    def get_by_id(self, id):
        for rec in self.data:
            if rec.get('id') == id:
                return rec

        return None

    def get_matching(self, query):
        res = []
        for rec in self.data:
            if self.matches(rec, query):
                res += [rec]

        return res

    def get_possible_values(self):
        res = []
        for item in self.data:
            res += item.values()
        return set(res)

    def get_slots(self):
        slots = set()
        for item in self.data:
            for key in item.keys():
                slots.add(key)
        return slots


