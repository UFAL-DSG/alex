#!/usr/bin/env python
# -*- coding: utf-8 -*-


def cudasolve(A, b, tol=1e-3, normal=False, regA = 1.0, regI = 0.0):
    """ Conjugate gradient solver for dense system of linear equations.

        Ax = b

        Returns: x = A^(-1)b

        If the system is normal, then it solves

        (regA*A'A +regI*I)x= b

        Returns: x = (A'A +reg*I)^(-1)b
    """

    N = len(b)
    b = b.reshape((N,1))
    b_norm = culinalg.norm(b)
    x = b.copy()
    if not normal:
        r = b - culinalg.dot(A,x)
    else:
        r = b - regA*culinalg.dot(A,culinalg.dot(A,x), transa='T') - regI*x
    p = r.copy()
    rsold = culinalg.dot(r,r, transa='T')[0][0].get()
    for i in range(N):
        if not normal:
            Ap = culinalg.dot(A,p)
        else:
            Ap = regA*culinalg.dot(A,culinalg.dot(A,p), transa='T') + regI*p

        pAp = culinalg.dot(p, Ap, transa='T')[0][0].get()
        alpha = rsold / pAp

        x += alpha*p
        r -= alpha*Ap
        rsnew = culinalg.dot(r,r, transa='T')[0][0].get()

        if math.sqrt(rsnew)/b_norm < tol:
            break
        else:
            p = r + (rsnew/rsold)*p
            rsold = rsnew

    return x.reshape(N)
