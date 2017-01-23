import parser
import sys


def main():
    p = parser.Parser(sys.stdin)
    p.parse()


if __name__ == "__main__":
    main()
