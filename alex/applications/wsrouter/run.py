if __name__ == '__main__':
    import autopath

from wsrouter import WSRouter


def main(addr, port, entry_timeout):
    router = WSRouter(addr, port, entry_timeout)
    router.run()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('addr')
    parser.add_argument('port', type=int)
    parser.add_argument('--entry_timeout', type=int, default=10)

    args = parser.parse_args()

    main(**vars(args))