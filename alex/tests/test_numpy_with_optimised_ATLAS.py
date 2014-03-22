#!/usr/bin/env python


def main():
    print "=" * 120
    print " If you can see that all your cores are running at 100% then you are using optimised ATLAS library."
    print "=" * 120
    print

    import numpy
# numpy.test()   #this should run with no errors (skipped tests and known-fails are ok)

    size = 8000

    if id(numpy.dot) == id(numpy.core.multiarray.dot):
        # A way to know if you use fast blas/lapack or not. However, it wont tell
        # you whetehr it is generric ATLAS or machine optimised version.
        print "Not using blas/lapack!"

    print "creating matrix"
    a = numpy.random.randn(size, size)

    print "multiplying matrix"
    numpy.dot(a.T, a)

    print "adding identity matrix"
    i = numpy.identity(size)
    a += i

    print "inverting matrix"
    inva = numpy.linalg.inv(a)


if __name__ == '__main__':
    main()
