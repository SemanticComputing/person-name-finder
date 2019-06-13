import logging, json
import re
import time
import datetime
import csv
import nltk
import nltk.data
from src.namefinder import NameFinder
import xml.dom.minidom
import xml.etree.ElementTree as ET
from src.las_query import lasQuery
from distutils.util import strtobool
from datetime import datetime as dt
from nltk.tokenize import word_tokenize
import numpy as np

class TextParser:
    def __init__(self, string):
        # input text
        self.string = string
        self.regex_check = dict()
        self.structure = dict()
        self.chunks = list()
        self.words = dict()
        self.lemma_words = dict()
        self.sentence_list = list()

        # settings

        self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai | S | V )'
        self.contextual_chunking_single_separators = [' S ', ' V ']
        self.context_birth_identifiers = ['s.', 'syntynyt']
        self.context_death_identifiers = ['k.', 'kuollut']
        self.context_lifespan_separators = ['-', '–']

    def parse_input(self, tokenizer):
        sentence_counter = 0
        chunk_counter = 0
        sentence_len = 0
        sentences = tokenizer.tokenize(self.string)
        for sentence in sentences:
            chunk_counter, sentence_counter, sentence_len = self.parse_string(sentence, sentence_counter, chunk_counter, sentence_len)
            sentence_counter += 1

        return self.chunks, self.structure, self.regex_check

    def parse_string(self, string, sentence_counter, chunk_counter, sentence_len):
        sentence_counter, chunk_counter, sentence_len = self.split_to_chunks(string, sentence_counter, chunk_counter, sentence_len)

        #for chunk in self.chunks:
        #    s = Sentence()
        #    s.set_sentence(chunk, "", counter, sentence_len)
        #    sentence_len += len(chunk) + 1
        #    counter += 1
        #    self.sentence_list.append(s)

        return chunk_counter, sentence_counter, sentence_len

    # Check if string contains a number
    # params
    #  inputString  - string to be checked
    # return
    #  boolean value True or False
    def has_numbers(self, inputString):
        return any(char.isdigit() for char in inputString)

    # Split sentences to text chunks to better identify names from comma separated lists and identify
    # contextual information
    # params
    #  string       - input string, sentence typically
    #  ord          - sentence order number
    #  chunk_counter- sentence chunk order number
    # return
    #  chunks       - list of text chunks or sentences
    #  structure    - dictionary of chunk structure to keep tract from which sentence each chunk is from
    #  regex_check  - list of contextual information in brackets such as dates
    def split_to_chunks(self, string, ord, chunk_counter, sentence_len):
        separators = [', ', '; ', ' (', ') ', ')', ' ja ', ' tai ', ' S ', ' V ']
        exceptional_separators = [' (', ') ']
        chunk_regex_check = 0
        splitted = re.split(self.string_chunking_pattern, string, ord)  # sentence.split('[,;]')

        if len(splitted) > 1:
            for chunk in splitted:
                if chunk not in separators and len(chunk)>0:
                    s = Sentence()
                    s.set_sentence(chunk, "", chunk_counter, sentence_len)
                    sentence_len += len(chunk) + 1
                    self.chunks.append(s)
                    if chunk_counter not in self.structure:
                        print("Add structure", chunk_counter, ord, chunk)
                        self.structure[chunk_counter] = ord
                        if chunk_regex_check > 0:
                            print("Check chunk? ", chunk)
                            if self.has_numbers(chunk):
                                print("This chunk has to be checked!")
                                print("Add chunk structure", regex_chunk_counter, ord)
                                if regex_chunk_counter not in list(self.regex_check.keys()):
                                    self.regex_check[regex_chunk_counter] = chunk
                                else:
                                    self.regex_check[regex_chunk_counter] += chunk
                        chunk_counter += 1
                elif chunk == ' (':
                    print('Start bracket checking')
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
                elif chunk == ')' or chunk == ') ':
                    chunk_regex_check = 0
                    print('End bracket checking')
                elif chunk in self.contextual_chunking_single_separators:
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
        else:
            s = Sentence()
            s.set_sentence(string, "", chunk_counter, sentence_len)
            sentence_len += len(string) + 1
            self.chunks.append(s)
            if chunk_counter not in self.structure:
                self.structure[chunk_counter] = ord
                chunk_counter += 1

        return ord, chunk_counter, sentence_len

class Sentence:
    def __init__(self):
        self.string = ""
        self.lemmatized = ""
        self.ord = None
        self.location = None
        self.regex_check = dict()
        self.words = dict()
        self.lemma_words = dict()

        # settings

        self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai | S | V )'
        self.contextual_chunking_single_separators = [' S ', ' V ']
        self.context_birth_identifiers = ['s.', 'syntynyt']
        self.context_death_identifiers = ['k.', 'kuollut']
        self.context_lifespan_separators = ['-', '–']

    def set_sentence(self, string="", lemma="", ord=None, location=None):
        self.string = string
        self.lemmatized = lemma
        self.ord = ord
        self.location = location

        self.word_tokenization(self.string)
        if len(lemma) < 1:
            self.lemmatized = self.lemmatize(string)
            self.lemma_words = self.word_tokenization(self.lemmatized)

    def get_regex_check_list(self):
        return self.regex_check

    def get_regex_check_item(self, id):
        if id in self.regex_check:
            return self.regex_check[id]

        return None

    def get_lemma(self):
        return self.lemmatized

    def add_lemma(self, lemma):
        self.lemmatized = lemma

    def split_to_words(self):
        pass

    def split_to_chunks(self):
        separators = [', ', '; ', ' (', ') ', ')', ' ja ', ' tai ', ' S ', ' V ']
        exceptional_separators = [' (', ') ']
        chunk_regex_check = 0
        result = list()
        structure = dict()
        counter = 0
        chunk_counter = 0
        splitted = re.split(self.string_chunking_pattern, self.string)  # sentence.split('[,;]')

        if len(splitted) > 1:
            for chunk in splitted:
                if chunk not in separators:
                    result.append(chunk)
                    if chunk_counter not in structure:
                        structure[chunk_counter] = self.ord
                        if chunk_regex_check > 0:
                            print("Check chunk? ", chunk)
                            if self.has_numbers(chunk):
                                print("This chunk has to be checked!")
                                if regex_chunk_counter not in list(self.regex_check.keys()):
                                    self.regex_check[regex_chunk_counter] = chunk
                                else:
                                    self.regex_check[regex_chunk_counter] += chunk
                        chunk_counter += 1
                elif chunk == ' (':
                    print('Start bracket checking')
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
                elif chunk == ')' or chunk == ') ':
                    chunk_regex_check = 0
                    print('End bracket checking')
                elif chunk in self.contextual_chunking_single_separators:
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
        else:
            result.append(self.string)
            if chunk_counter not in structure:
                structure[chunk_counter] = self.ord
                chunk_counter += 1

        return result, structure, self.regex_check

    def word_tokenization(self, string):
        words_dct = dict()
        prev = 0
        string_len = len(string)
        words = word_tokenize(string)
        for word in words:
            end_ind = len(word) + prev
            w = Word(word, prev, end_ind)
            words_dct[word]=w
            if end_ind < string_len:
                prev += end_ind + 1
            else:
                print("End of a string!")
                prev = end_ind

        return words_dct

    def has_numbers(self, inputString):
        return any(char.isdigit() for char in inputString)

    def do_lemmatization(self, sentence_data, indeces):
        output = dict()
        index_lists = dict()
        for i in range(0, len(sentence_data)):
            output[i] = self.lemmatize(sentence_data[i])

            index_lists[i] = indeces[i]
            print("Index list:", i, indeces[i], sentence_data[i])

        # {i: lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
        return output, index_lists

    def lemmatize(self, text):
        las = lasQuery()
        lemmatized = las.lexical_analysis(text, 'fi')
        print("Lemmatized:", lemmatized)
        return lemmatized

    def find_name_location(self, name):
        word_list = list(self.words.keys())
        lemma_list = list(self.lemma_words.keys())
        name_list = word_tokenize(name)
        print("Word listing:",word_list)
        print("Lemma listing:", lemma_list)
        print("Name listing:", name_list)

        ind = self.find_subarray(np.array(lemma_list), np.array(name_list))
        end_ind = len(name_list)

        start = self.words[word_list[ind]]
        stop = self.words[word_list[end_ind]]

        if start != None and stop != None:
            return start.get_start_location(), stop.get_end_location()

        return None, None

    def find_subarray(self, a,b):
        return a.tostring().index(b.tostring()) // a.itemsize

class Word:
    def __init__(self, string, start_ind, end_ind):
        self.string = string
        self.start_location = start_ind
        self.end_location = end_ind

    def get_start_location(self):
        return self.start_location

    def get_end_location(self):
        return self.end_location
