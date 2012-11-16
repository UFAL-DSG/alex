import inspect

def interface_method(f):
    f.abstract = True
    return f

class Interface(object):
    def __new__(cls, *args, **kwargs):
        res = super(Interface, cls).__new__(cls, *args, **kwargs)

        missing_methods = []
        for method in inspect.getmembers(res, predicate=inspect.ismethod):
            if getattr(method[1], 'abstract', False):
                missing_methods += [method[0]]

        if len(missing_methods) > 0:
            raise Exception("Class %s is missing these interface methods: %s" %\
                            (cls.__name__,", ".join((missing_methods))))

        return res

