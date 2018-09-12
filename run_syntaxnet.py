import argparse
from argparse import RawTextHelpFormatter
import logging

import numpy as np
import pandas as pd
import csv
from nltk.stem import WordNetLemmatizer
import time
import re
import os


def main(args):
    print('Preprocessing documents...')

    # Загружаем коллекцию, удаляем пунктуацию и переводим в нижний регистр.
    # Получаем список предложений
    sentences = []
    document_ids = []

    for doc_id, filename in enumerate(os.listdir(args.collection)):
        with open(args.collection + "/" + filename, "r") as f:
            sentences_raw = f.read().split('.')

        for sentence in sentences_raw:
            sentence_nopunct = re.sub("[^A-Za-zА-Яа-я ]", '', sentence)
            sentence_nopunct = sentence_nopunct.lower().strip()
            if len(sentence_nopunct) > 1:
                sentences.append(sentence_nopunct)
                document_ids.append(doc_id)

    # Если выход синтакснета уже есть -> пропускаем это шаги
    syntaxnet_ready_flag = args.syntaxnet_ready != ""
    if not syntaxnet_ready_flag:

        # Запишем в файл каждое предложение в отдельной строке
        syntaxnet_input_filename = 'tmp' + '_' + str(os.getpid()) + '_' + str(int(time.time())) + 'input' + '.txt'

        with open(syntaxnet_input_filename, "w") as f:
            for sentence in sentences:
                f.write("{}\n".format(sentence))

        print('Running syntaxnet...')

        if args.syntaxnet_out != "":
            syntaxnet_output_filename = args.syntaxnet_out
        else:
            syntaxnet_output_filename = 'tmp' + '_' + str(os.getpid()) + '_' + str(int(time.time())) + 'output' + '.txt'

        # Прогоняем полученный файл через SyntaxNet
        start_time = time.time()
        os.system("cat {} | docker run --rm -i inemo/syntaxnet_eng > {} 2> /dev/null".format(
            syntaxnet_input_filename, syntaxnet_output_filename
        ))
        print("It took {:.2f} s.".format(time.time() - start_time))

        os.system(' '.join(['rm', syntaxnet_input_filename]))
        if args.syntaxnet_out == "":
            os.system(' '.join(['rm', syntaxnet_output_filename]))

    else:
        print("We already have syntaxnet output")
        syntaxnet_output_filename = args.syntaxnet_ready

    print('Postprocessing syntaxnet results...')
    syntaxnet_out = pd.read_table(syntaxnet_output_filename, header=None,
                                  dtype={0: np.int, 6: np.int},
                                  quoting=csv.QUOTE_NONE, engine='c'
                                 )[[0, 1, 3, 6, 7]].fillna("")

    syntaxnet_out.rename(columns={0: "word_id", 1: "word", 3: "POS",
                                  6: "parent_id", 7: "dependency"},
                         inplace=True)

    # К каждому слову добавим id предложения и его лемму
    # Нам повезло, что SyntaxNet говорит нам о части речи слова, так как это повысит качетсво лемматизатора
    lemmatizer = WordNetLemmatizer()

    syntaxnet_out["word_id"] -= 1
    syntaxnet_out["parent_id"] -= 1

    cur_sentence_id = -1
    sentence_ids = []
    lemmas = []

    for row in syntaxnet_out.itertuples():
        word_id, word, pos = row.word_id, row.word, row.POS
        if word_id == 0:
            cur_sentence_id += 1

        if pos == "VERB":
            lemma = lemmatizer.lemmatize(word, pos='v')
        elif pos == "ADJ":
            lemma = lemmatizer.lemmatize(word, pos='a')
        elif pos == "ADV":
            lemma = lemmatizer.lemmatize(word, pos='r')
        else:
            lemma = lemmatizer.lemmatize(word, pos='n')

        lemmas.append(lemma)
        sentence_ids.append(cur_sentence_id)

    syntaxnet_out["sentence_id"] = sentence_ids
    syntaxnet_out["lemma"] = lemmas

    # Добавим id и имя документа к каждому слову, чтобы опять собрать коллекцию
    document_names = os.listdir('./Data/Input/collection/')

    i = 0
    doc_ids = []
    doc_names = []
    prev_sentence_id = 0
    for sentence_id in syntaxnet_out["sentence_id"]:
        if sentence_id != prev_sentence_id:
            i += 1
            prev_sentence_id = sentence_id
        doc_ids.append(document_ids[i])
        doc_names.append(document_names[doc_ids[-1]])
    syntaxnet_out["doc_id"] = doc_ids
    syntaxnet_out["doc_name"] = doc_names

    # Сохраняем в таблицу выход syntaxnet'а
    print('Saving syntaxnet output')
    syntaxnet_out.to_csv(args.o, sep='\t', index=False)

    # Записываем полученную лемматизированную коллекцию в файл
    if args.lemmatize != "":
        print("Saving lemmatized collection...")

        prev_doc_id = 0
        prev_sentence_id = 0
        cur_text = ""
        for row in syntaxnet_out.itertuples():
            lemma = row.lemma
            sentence_id, doc_id = row.sentence_id, row.doc_id
            doc_name = row.doc_name

            if sentence_id != prev_sentence_id:
                cur_text += ' .'
                prev_sentence_id = sentence_id
            if doc_id != prev_doc_id:
                with open(args.lemmatize + '/' + doc_name, "w") as f:
                    f.write(cur_text)
                cur_text = ""
                prev_doc_id = doc_id
            # do not add space at start of document
            if(len(cur_text) != 0):
                cur_text += ' '
            cur_text += lemma


    print("Done!")
    print("")
    print("Stats:")
    print("sentences:\t{}".format(len(sentences)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        """Run syntaxnet, postprocess and save result in csv file""",
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet",
                        help="print nothing to stdout",
                        action="store_true")
    parser.add_argument("collection",
                        help="directory with documents",
                        metavar="collection")
    parser.add_argument("-o", default="syntax.csv", metavar="output",
                        help="csv table with results of syntaxnet")
    parser.add_argument("--lemmatize", default="", metavar="dir",
                        help="save lemmatized collection to directory")
    parser.add_argument("--syntaxnet_out", default="", metavar="syntaxnet_output",
                        help="save syntaxnet output to file")
    parser.add_argument("--syntaxnet_ready", default="", metavar="syntaxnet_output",
                        help="not to run syntaxnet if you have output from previous session")
    args = parser.parse_args()

    # for easy quiet output
    print = logging.info
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    main(args)
