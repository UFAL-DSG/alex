# TODO: Put this into the __init__.py of alex.utils.
import os


def root():
    """
    Finds the root of the project and return it as string.

    The root is the directory named alex.

    """

    path, directory = os.path.split(os.path.abspath(__file__))

    while directory and directory != 'alex':
        path, directory = os.path.split(path)

    if directory == 'alex':
        return os.path.join(path, directory)
    else:
        raise Exception("Couldn't determine path to the project root.")
