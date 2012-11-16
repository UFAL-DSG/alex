import os

def root():
    """Find the root of the project and return it as string."""

    path, directory = os.path.split(os.path.abspath(__file__))

    while directory and directory != 'SDS':
        path, directory = os.path.split(path)

    if directory == 'SDS':
        return os.path.join(path, directory)
    else:
        raise Exception("Couldn't determine path to the project root.")
