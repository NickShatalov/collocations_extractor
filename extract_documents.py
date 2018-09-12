# current code uses wikiextractor project
# see more: https://github.com/attardi/wikiextractor


import argparse
from argparse import RawTextHelpFormatter
import logging

import os
import time
import json
import re


def main(args):
    print("Extracting texts...")

    # Обрабатываем текст с помощью wikiextractor. Получаем json файлы
    json_directory_name = 'tmp' + '_' + str(os.getpid()) + '_' + str(int(time.time())) + '/'
    os.system(' '.join([args.wikiextractor, "-q", "--json ", "-o", json_directory_name, args.input_xml]))

    # Читаем их
    texts_str = ""
    for subdir in os.listdir(json_directory_name):
        for file in os.listdir(json_directory_name + "/" + subdir):
            with open(json_directory_name + "/" + subdir + "/" + file, "r") as f:
                texts_str += f.read()

    texts = []
    for text in texts_str.split('\n'):
        if text != '':  # in case of double \n
            texts.append(json.loads(text))

    # Сохраняем полученные документы в коллекцию + миниобработка
    for text in texts:
        filename = text["title"]
        filename = re.sub("[^A-Za-zА-Яа-я0-9 ]", "", filename)
        filename = re.sub(" +", "_", filename)
        article = '\n'.join(text["text"].split('\n')[2:])  # remove name of article at the start
        with open(args.o + "/" + filename + ".txt", "w") as f:
            f.write(article)

    # Удаляем уже не нужную директорию с json файлами
    os.system(' '.join(['rm', '-rf', json_directory_name]))

    print("Done!")
    print("")
    print("Stats:")
    print("documents:\t{}".format(len(texts)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        """Extract documents (text only) from xml file""",
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet",
                        help="print nothing to stdout",
                        action="store_true")
    parser.add_argument("input_xml",
                        help="xml file with documents",
                        metavar="xml_input")
    parser.add_argument("--wikiextractor", default="WikiExtractor.py",
                        help="location of wikiextractor")
    parser.add_argument("-o", default="collection", metavar="output_dir",
                        help="directory to save documents in (one doc per one file)")
    args = parser.parse_args()

    # for easy quiet output
    print = logging.info
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    main(args)
