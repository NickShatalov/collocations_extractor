import argparse
from argparse import RawTextHelpFormatter
import logging

import numpy as np
import pandas as pd
import os
from tqdm import tqdm


def colloc_in_sentence(colloc, sentence):
    """
        Check if collocation is in sentence
        :param colloc -- str,
        :param sentence -- str
    """
    sent_words = sentence.split(' ')
    colloc_words = colloc.split(' ')
    for i in range(len(sent_words) - len(colloc_words) + 1):
        if sent_words[i] == colloc_words[0]:
            flag = True
            for j, word in enumerate(colloc_words[1:], 1):
                if sent_words[i + j] != word:
                    flag = False
                    break
            if flag:
                return True
    return False

def main(args):
    print("Processing Syntaxnet output...")

    # Открываем сырой выход синтакснета
    with open(args.input, "r") as f:
        syntaxnet_out = f.read()

    # Лемматизированные предложения для поиска кандидатов-коллокаций
    lemmatized_sentences = []
    for filenane in os.listdir(args.lemmatized_collection):
        with open(args.lemmatized_collection + '/' + filenane, "r") as f:
            lemmatized_sentences += [sent.strip() for sent in f.read().split(".")]
    # Сюда как-то попали пустые предложения
    lemmatized_sentences = [sent for sent in lemmatized_sentences if sent != '']

    # Непосредсдственно сами кандидаты
    # with open(args.topmine_data, "r") as f:
    #     topmine_collocs = f.read().split("\n")
    topmine_df = pd.read_csv(args.topmine_data, sep='\t')
    topmine_collocs = list(topmine_df['ngramm'])
    del topmine_df


    # Создаем список с зависимостями
    processed_sentences = []
    sentence = []
    for line in syntaxnet_out.split("\n"):
        if len(line) == 0:
            processed_sentences.append(sentence)
            sentence = []
        else:
            word = line.split("\t")
            sentence.append(word)

    deps = []
    for sentence in processed_sentences:
        s = ''
        for line in sentence:
            s += "\t".join(line) + '\n'
        deps.append(s)
    del deps[-1] # empty sentence

    # Находим коллокации в предложениях и синтаксических деревьях
    # Подсчитываем расстояния между словами
    res_dict = dict()
    for lemmatized_sentence, dep in tqdm(zip(lemmatized_sentences, deps), total=len(deps)):
        dependencies = [[line.split('\t')[i] for i in [0, 1, 6]] for line in dep.split('\n')[:-1]]

        for colloc in topmine_collocs:
            if colloc_in_sentence(colloc, lemmatized_sentence):
                colloc_idx = []
                for i in range(len(lemmatized_sentence.split(' ')) - len(colloc.split(' ')) + 1):
                    if (lemmatized_sentence.split(' ')[i:i + len(colloc.split(' '))] == colloc.split(' ')):
                        colloc_idx.append(i)

                branches = []
                for i in colloc_idx:
                    for k in range(i, i + len(colloc.split(' '))):
                        branch = [k + 1]
                        j = k
                        while True:
                            branch.insert(0, int(dependencies[j][2]))
                            j = int(dependencies[j][2]) - 1
                            if j == -1:
                                break
                        branches.append(branch)

                distances = []
                for i in range(len(branches)):
                    for j in range(i + 1, len(branches)):
                        branch1, branch2 = branches[i], branches[j]
                        flag = False
                        for k in range(min(len(branch1), len(branch2))):
                            if branch1[k] != branch2[k]:
                                distances.append(len(branch1[k:]) + len(branch2[k:]))
                                flag = True
                                break
                        if not flag:
                            distances.append(abs(len(branch1) - len(branch2)))

                dist = np.array(distances).max() # - len(colloc.split(' ')) + 1
                if colloc in res_dict:
                    res_dict[colloc].append(dist) # мб поменять стратегию
                else:
                    res_dict[colloc] = [dist]

        mean_dict = dict()
        for k, v in res_dict.items():
            mean_dict[k] = np.array(v).mean()

        keys = []
        values = []
        for k in mean_dict:
            keys.append(k)
            values.append(mean_dict[k])
        df = pd.DataFrame({'collocation': keys, 'syntax_distance': values})
        df.to_csv(args.o, sep='\t', index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        """Run syntaxnet, postprocess and save result in csv file""",
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet",
                        help="print nothing to stdout",
                        action="store_true")
    parser.add_argument("input",
                        help="document with raw syntaxnet output",
                        metavar="input")
    parser.add_argument("-o", default="syntaxnet.tsv", metavar="output",
                        help="csv table with extracted features by syntaxnet")
    # parser.add_argument("--collocations_output", default="", metavar="colloc_out",
    #                     help="file with collocations which were selected by syntaxnet")
    parser.add_argument("--lemmatized_collection", metavar="collection",
                        help="lemmatized collection")
    parser.add_argument("--topmine_data", metavar="topmine_tsv",
                        help="data extracted with topmine")
    args = parser.parse_args()

    # for easy quiet output
    print = logging.info
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(message)s")

    main(args)
