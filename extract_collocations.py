import argparse
from argparse import RawTextHelpFormatter
import logging

from bs4 import BeautifulSoup
import re


def main(args):
    print("Extracting collocations from hyperlinks...")

    # Выделяем текст статьи из xml файла
    with open(args.input_xml, "r") as f:
        data_xml = f.read().replace('\n', ' ')
    soup = BeautifulSoup(data_xml, "xml")
    texts = [tmp.text for tmp in soup.find_all('text')]

    # Выделяем гиперссылки
    hyperlinks = []
    for text in texts:
        for open_brackets, close_brackets in zip(re.finditer('\[\[', text), re.finditer('\]\]', text)):
            start_ind, close_ind = open_brackets.span()[1], close_brackets.span()[0]
            hyperlinks.append(text[start_ind:close_ind])

    # Фильтруем теги, разбиваем ссылки с множественными словами
    filtered_hyperlinks = []
    for hl in hyperlinks:
        # - Теги
        # Игнорируем, если тег File:
        if re.match("File:", hl) and (re.match("File:", hl).span()[0] == 0):
            continue
        # Добавляем имя категории из тега Category:
        if re.match("Category:", hl) and (re.match("Category:", hl).span()[0] == 0):
            filtered_hyperlinks.append(hl[re.match("Category:", hl).span()[1]:])
            continue

        # - НеТеги
        # Убираем все что в скобках
        hl = re.sub("\(.+\)", "", hl)
        # Разделяем мультиназвания (через | или and) на раздельные коллокации
        sub_hl = list(re.split("\|| and ", hl))
        filtered_hyperlinks += sub_hl

    # Окончательная обработка, получаем коллокации
    collocs = []
    for hl in filtered_hyperlinks:
        hl = hl.strip().lower()

        # Если это инициалы -> не добавляем
        if re.match("(.\. .\. .+)|(.+ .\. .+)", hl) and (len(hl.split(' ')) == 3):
            continue

        hl = re.sub(" +", " ", hl)
        hl = re.sub("[^ A-Za-z-]+", "", hl)
        hl = hl.strip()

        flag = (hl not in collocs) and \
               (len(hl.split(' ')) >= args.min) and \
               (len(hl.split(' ')) <= args.max)
        if flag:
            collocs.append(hl)

    with open(args.o, "w") as f:
        f.write('\n'.join(collocs))

    print("Done!")
    print("")
    print("Stats:")
    print("hyperlinks:\t{}".format(len(hyperlinks)))
    print("filtered hl:\t{}".format(len(filtered_hyperlinks)))
    print("collocations:\t{}".format(len(collocs)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        """Extract collocations from hyperlinks in xml file""",
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet",
                        help="print nothing to stdout",
                        action="store_true")
    parser.add_argument("input_xml",
                        help="xml file with documents",
                        metavar="xml_input")
    parser.add_argument("-o", default="gt_collocs.txt", metavar="output",
                        help="file to write collocs in (one colloc in each line)")
    parser.add_argument("--min", default=2, metavar="min_len", type=int,
                        help="extract collocations with minimum length min_len")
    parser.add_argument("--max", default=5, metavar="max_len", type=int,
                        help="extract collocations with maximum length max_len")
    args = parser.parse_args()

    # for easy quiet output
    print = logging.info
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    main(args)
