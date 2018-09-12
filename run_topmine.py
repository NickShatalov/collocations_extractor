import argparse
from argparse import RawTextHelpFormatter
import logging

import ngrammer
import pandas as pd
import os


def main(args):
    print("Running TopMine...")

    # Загружаем лемматизированную коллекцию и стоп-слова
    corpora = []

    for doc_id, filename in enumerate(os.listdir(args.collection)):
        with open(args.collection + '/' + filename, "r") as f:
            corpora.append(f.read().split(' '))

    if args.stopwords != "":
        with open(args.stopwords, "r") as f:
            stopwords = f.read().split('\n')
    else:
        stopwords = []

    # Запускаем ngrammer
    ng = ngrammer.NGrammer()
    ng.delimiters = stopwords
    ng.delimiters_regex = ['[^a-z ]+']

    ng.frequentPhraseMining(corpora, args.threshold)
    frequencies = ng._phrase2freq

    ngramms = []
    for document in corpora:
        res = ng.ngramm(document, threshhold=args.threshold)
        ngramms += res[0]

    # delete points and stopwords
    ngramms = [ngramm for ngramm in ngramms if (ngramm != '.') and (ngramm not in stopwords)]

    # Оставим только ngramm'ы, в которых больше одного токена и они не повторяются
    unique_ngramms = []
    for ngramm in ngramms:
        if (ngramm not in unique_ngramms) and (len(ngramm.split(' ')) > 1):
            unique_ngramms.append(ngramm)

    if args.collocations_output != "":
        # Запишем полученные уникальные ngramm'ы в файл
        with open(args.collocations_output, "w") as f:
            f.write("\n".join(unique_ngramms))

    print("Collecting features...")

    # Запишем в файл все коллокации с данными, которые получил topmine
    freqs = ng._phrase2freq
    scores = ng._significanceScores

    ngramm_list = []
    freq_list = []
    score_list = []
    for k, v in scores.items():
        ngramm_list.append(k)
        freq_list.append(freqs.get(k))
        score_list.append(scores[k])

    df = pd.DataFrame({
        'ngramm': ngramm_list,
        'freq': freq_list,
        'score': score_list
    })
    df = df.dropna()
    df.to_csv(args.o, sep='\t', index=False)

    print("Done!")
    print("")
    print("Stats:")
    print("stopwords:\t\t\t{}".format(len(stopwords)))
    print("ngramms with features:\t\t{}".format(df.shape[0]))
    print("extracted unique ngramms:\t{}".format(len(unique_ngramms)))


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
                        help="directory with lemmatized documents",
                        metavar="collection")
    parser.add_argument("-o", default="topmine.csv", metavar="output",
                        help="csv table with results of topmine")
    parser.add_argument("--collocations_output", default="", metavar="colloc_out",
                        help="file with collocations which were selected by topmine")
    parser.add_argument("--stopwords", default="", metavar="stopwords",
                        help="file with stopwords (as delimeters)")
    parser.add_argument("--threshold", default=3, type=float, metavar="threshold",
                        help="threshold for topmine")
    args = parser.parse_args()

    # for easy quiet output
    print = logging.info
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    main(args)
