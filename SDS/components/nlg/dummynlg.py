#!/usr/bin/env python

class DummyNLG(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def generate_inform(self, dai):
        if dai.name == "food":
            res = ["It serves %s food" % dai.value]
        elif dai.name == "name":
            res = ["The place is called %s" % dai.value]
        elif dai.name == "pricerange":
            res = ["The prices are %s" % dai.value]
        elif dai.name == "price":
            res = [dai.value]
        elif dai.name == "area":
            res = ["It is located in the %s area" % dai.value]
        elif dai.name == "addr":
            res = ["Address of the place is %s" % dai.value]
        elif dai.name == "phone":
            res = ["Its phone number is %s" % dai.value]
        else:
            res = ["The %s is %s." % (dai.name, dai.value,)]

        return res

    def generate_want(self, dai):
        if dai.name == "food":
            res = ["You want it to serve %s food" % dai.value]
        elif dai.name == "name":
            res = ["You want a place called %s" % dai.value]
        elif dai.name == "pricerange":
            res = ["You want %s pricerange" % dai.value]
        elif dai.name == "area":
            res = ["You want something in the %s area" % dai.value]
        else:
            res = ["You want %s to be %s" % (dai.name, dai.value,)]

        return res


    def generate(self, da):
        res = []
        for dai in da:
            if dai.dat == "hello":
                res += ["Hello. How may I help you?"]
            if dai.dat == "anythingelse":
                res += ["Is there anything else I can help you with?"]
            elif dai.dat == "inform":
                res += self.generate_inform(dai)
                res += ["and"]
            elif dai.dat == "noentiendo":
                res += ["Sorry I didn't understand you?"]
            elif dai.dat == "nomatch":
                res += ["Sorry, there is no place matching your criterion."]
            elif dai.dat == "want":
                res += self.generate_want(dai)
                res += ["and"]
            elif dai.dat == "affirm":
                res += ["Yes"]
            elif dai.dat == "negate":
                res += ["No"]
            elif dai.dat == "noclue":
                res += ["Sorry, I don't know about the %s of this place." % dai.name]
            elif dai.dat == "instructions":
                res += ["I can give you information about places to eat in the town. Just specify what kind of food you want, area of the town or price range."]
            else:
                res += ["I want to %s that %s is %s." % \
                        (dai.dat, dai.name, dai.value, )]

        if res[-1] == "and":
            res = res[:-1]

        return " ".join(res)
