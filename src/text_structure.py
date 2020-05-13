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
from collections import OrderedDict

class TextParser:
    def __init__(self, string):
        # input text
        self.string = string
        self.regex_check = dict()
        self.structure = dict()
        self.chunks = list()
        self.words = dict()
        self.lemma_words = dict()
        self.sentence_list = dict()
        self.sentence_chunks = dict()

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
        print("[TOKENIZED] ", sentences)
        for sentence in sentences:
            chunk_counter, sentence_counter, sentence_len = self.parse_string(sentence, sentence_counter, chunk_counter, sentence_len)
            sentence_counter += 1

        return self.chunks, self.structure, self.regex_check, self.sentence_list

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
        print("Sentence:", string)
        print("Split:", splitted)
        sen = Sentence()
        sen.set_sentence(ord=ord, string=string, chunks=splitted)
        self.sentence_list[ord]=sen
        self.sentence_chunks[sen] = list()

        if len(splitted) > 1:
            for chunk in splitted:
                if chunk not in separators and len(chunk)>0:
                    s = SentenceChunk()

                    s.set_sentence_chunk(chunk, "", chunk_counter, sentence_len)

                    sentence_len += len(chunk) + 1
                    self.chunks.append(s)
                    self.sentence_chunks[sen].append(s)
                    if chunk_counter not in self.structure:
                        #print("Add structure", chunk_counter, ord, chunk)
                        self.structure[chunk_counter] = ord
                        if chunk_regex_check > 0:
                            #print("Check chunk? ", chunk)
                            if self.has_numbers(chunk):
                                #print("This chunk has to be checked!")
                                #print("Add chunk structure", regex_chunk_counter, ord)
                                if regex_chunk_counter not in list(self.regex_check.keys()):
                                    self.regex_check[regex_chunk_counter] = chunk
                                else:
                                    self.regex_check[regex_chunk_counter] += chunk
                        chunk_counter += 1
                elif chunk == ' (':
                    #print('Start bracket checking')
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
                elif chunk == ')' or chunk == ') ':
                    chunk_regex_check = 0
                    #print('End bracket checking')
                elif chunk in self.contextual_chunking_single_separators:
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
        else:
            s = SentenceChunk()
            s.set_sentence_chunk(string, "", chunk_counter, sentence_len)
            sentence_len += len(string) + 1
            self.chunks.append(s)
            self.sentence_chunks[sen].append(s)
            if chunk_counter not in self.structure:
                self.structure[chunk_counter] = ord
                chunk_counter += 1

        return ord, chunk_counter, sentence_len

    def find_sentence_for_chunk(self, chunk):
        for sentence, chunks in self.sentence_chunks.items():
            if chunk in chunks:
                return sentence


class Sentence:
    def __init__(self):
        self.ord = 0
        self.string = ""
        self.chunks = list()
        self.chunk_obj = OrderedDict()
        self.chunk_sizes = dict()

    def set_sentence(self, ord=0, string="", chunks=list()):
        self.ord = ord
        self.string = string
        self.chunks = chunks
        length=0
        for c in chunks:
            self.chunk_obj[c] = None
            self.chunk_sizes[c] = length
            length += len(c)

    def add_chunk_obj(self, chunk, string):
        self.chunk_obj[string] = chunk
        chunk.set_str_starts(self.chunk_sizes[string])

    def get_sentence_string(self):
        return self.string

class SentenceChunk:
    def __init__(self):
        self.string = ""
        self.lemmatized = ""
        self.ord = None
        self.location = None
        self.regex_check = dict()
        self.words = OrderedDict()
        self.word_ind_dict = dict()
        self.lemma_words = OrderedDict()
        self.str_starts = 0

        # settings

        self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai | S | V )'
        self.contextual_chunking_single_separators = [' S ', ' V ']
        self.context_birth_identifiers = ['s.', 'syntynyt']
        self.context_death_identifiers = ['k.', 'kuollut']
        self.context_lifespan_separators = ['-', '–']

    def set_sentence_chunk(self, string="", lemma="", ord=None, location=None):
        self.string = string
        self.lemmatized = lemma
        self.ord = ord
        self.location = location

        self.words = self.word_tokenization(self.string)
        if len(lemma) < 1:
            self.lemmatized = self.lemmatize(string)
            self.lemma_words = self.word_tokenization(self.lemmatized)

    def set_str_starts(self, start):
        self.str_starts = start

    def get_str_starts(self):
        return self.str_starts


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
        print("Sentence:", self.string)
        print("Split:", splitted)

        if len(splitted) > 1:
            for chunk in splitted:
                if chunk not in separators:
                    result.append(chunk)
                    if chunk_counter not in structure:
                        structure[chunk_counter] = self.ord
                        if chunk_regex_check > 0:
                            #print("Check chunk? ", chunk)
                            if self.has_numbers(chunk):
                                #print("This chunk has to be checked!")
                                if regex_chunk_counter not in list(self.regex_check.keys()):
                                    self.regex_check[regex_chunk_counter] = chunk
                                else:
                                    self.regex_check[regex_chunk_counter] += chunk
                        chunk_counter += 1
                elif chunk == ' (':
                    #print('Start bracket checking')
                    chunk_regex_check = 1
                    regex_chunk_counter = chunk_counter - 1
                elif chunk == ')' or chunk == ') ':
                    chunk_regex_check = 0
                    #print('End bracket checking')
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
        punct = ['.','?',';',',','!']
        words_dct = OrderedDict()
        prev = 0
        strlen = 0
        string_len = len(string)
        words = word_tokenize(re.sub(r'([A-ZÄÖÅa-zäöå0-9]+):([A-ZÄÖÅa-zäöå0-9]+)', r'\1__\2', string))
        #words = word_tokenize(string)
        #print("WORDS:", words)
        for word in words:
            if '__' in word:
                word = word.replace('__', ':')

            if strlen!= 0 and word not in punct:
                strlen+=1
            prev += 1
            end_ind = len(word) + strlen
            #print(word, strlen, end_ind, len(word))
            w = Word(word, strlen, end_ind)
            word_ind = str(word) + "_" + str(prev)# + "_" + str(end_ind)
            words_dct[word_ind]=w
            self.word_ind_dict[word_ind]=word

            if end_ind < string_len:
                if strlen == 0:
                    strlen = end_ind + 1
                else:
                    strlen = end_ind +1
            else:
                #print("End of a string!")
                strlen = end_ind

        return words_dct

    def has_numbers(self, inputString):
        return any(char.isdigit() for char in inputString)

    def do_lemmatization(self, sentence_data, indeces):
        output = dict()
        index_lists = dict()
        for i in range(0, len(sentence_data)):
            output[i] = self.lemmatize(sentence_data[i])

            index_lists[i] = indeces[i]
            #print("Index list:", i, indeces[i], sentence_data[i])

        # {i: lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
        return output, index_lists

    def lemmatize(self, text):
        las = lasQuery()
        lemmatized = las.lexical_analysis(text, 'fi')
        #print("Lemmatized:", lemmatized)
        return lemmatized

    def find_name_location(self, name, prev_start, prev_end):
        word_list = [w.get_string() for w in self.words.values()] #list(self.words.keys())
        lemma_list = [w.get_string() for w in self.lemma_words.values()]
        name_list = word_tokenize(name)
        #print("Words:", self.words)
        #print("Word listing:",word_list)
        #print("Lemma listing:", lemma_list)
        #print("Name listing:", name_list)
        ind = -1

        #subarray_ind = self.find_subarray(np.array(word_list), np.array(lemma_list), np.array(name_list), prev_start, prev_end)
        indeces = self.find_original_string_location(list(name_list), list(lemma_list), prev_start, prev_end)
        #print("Found subarray:", subarray_ind)
        print("list index:", indeces, lemma_list, name_list)
        for name,inds in indeces.items():
            #print("LOOP:",name, inds)
            for ind in inds:
                #if index > 0:
                #    ws = [w for w in word_list[0:indeces]]
                #    lens = [len(w)+1 for w in word_list[0:indeces]]
                #    print("words:", word_list[0:indeces], ind, lens, ws)
                #    ind = sum(lens)+1
                #else:
                    #ind = subarray_ind
                #    return None, None
                #ind = sum([w for w in range(word_list) if int(w) <= int(word_ind)])
                if ind == -1:
                    return None, None
                end_ind = ind + len(name_list) -1
                #end_ind = ind+len(word_list[subarray_ind])

                #print("INDEX:",ind, end_ind,word_list[ind]+"_"+str(ind+1), indeces)
                #print("comp",ind,  prev_start,self.words[word_list[ind]+"_"+str(ind+1)].get_start_location(), lemma_list[ind], name)
                #if self.words[word_list[ind]+"_"+str(ind+1)].get_start_location() > prev_start:
                #    print("ind checks")
                #if name == lemma_list[ind]:
                #    print("name checks")
                ##print("start, end:", word_list[subarray_ind], "/", word_list[subarray_ind])
                ##print("Start:", word_list[subarray_ind]+"_"+str(ind)+"_"+str(ind+len(word_list[subarray_ind])))
                ##print("End:",word_list[subarray_ind]+"_"+str(ind)+"_"+str(ind+len(word_list[subarray_ind])))
                #print(self.words[word_list[ind]+"_"+str(ind+1)].get_start_location(), prev_start)
                #print(name,lemma_list[ind])

                print("ind, wordlist[ind]",ind, word_list[ind])
                print("word_list[ind]+_+str(ind+1)",word_list[ind]+"_"+str(ind+1))
                print("prev_start",prev_start)
                print(self.words[word_list[ind]+"_"+str(ind+1)].get_start_location())
                print("name == lemma_list[ind]",name,lemma_list[ind])
                if self.words[word_list[ind]+"_"+str(ind+1)].get_start_location() > prev_start and name == lemma_list[ind]:
                    print("--->", word_list[ind]+"_"+str(ind+1))
                    #print("start:", self.words[word_list[ind]+"_"+str(ind+1)])
                    #print("stop:", self.words[word_list[ind] + "_" + str(ind+1)])
                    start = self.words[word_list[ind]+"_"+str(ind+1)]
                    stop = self.words[word_list[ind]+"_"+str(ind+1)]

                    print(start, stop)

                    #print("INDEX:",start, stop)
                    #print("--->",start.get_start_location(), stop.get_end_location())

                    if start != None and stop != None:
                        print("All good")
                        #text = "The cat sat on the mat"
                        #text = text[:8] + "slept" + text[11:]
                        #print("Test:", name, start.get_start_location(), "-", stop.get_end_location())
                        #print("START: ", self.string[:start.get_start_location()] )
                        #print("END: ", self.string[stop.get_end_location():])
                        #test = self.string[:start.get_start_location()] + "###" + self.string[stop.get_end_location():]

                        #print("Name LOC check:", test, "(",name,")", "/",  self.string)

                        return self.str_starts + start.get_start_location(), self.str_starts + stop.get_end_location()

        return None, None

    def find_from_text(self, start, end):
        try:
            if start != None and end != None:
                values = self.words.values()
                org_form = ""
                #print("printing values:",values)
                for v in values:
                    #print("Value", v)
                    if v.get_start_location() == start and v.get_end_location() == end:
                        return v.get_string()
                    elif v.get_start_location() >= start and v.get_end_location() < end:
                        if org_form == "":
                            org_form = v.get_string()
                        else:
                            org_form = org_form + " " + v.get_string()
                    elif v.get_start_location() > start and v.get_end_location() == end:
                        org_form = org_form + " " + v.get_string()
                        return org_form
                return org_form
        except Exception as err:
            print("[Exception] Error happened while trying to find original formed string, ", start, end, self.words)

        return None

    def find_subarray(self,c,a,b,prevstart,prevend):
        print("[find_subarray]:",a, b)
        word = self.detokenize(b)
        sentence = self.detokenize(a)
        results = list()

        print("[find_subarray]: sentence = ", sentence)
        print("[find_subarray]: word = ", word)
        #print("[find_subarray]:", p)
        #if b.tostring() in a.tostring():
        #    print(a.tostring().index(b.tostring()))  # a.itemsize
        for match in re.finditer(word, sentence):
            print("[find_subarray]:",match.start(), match.end(),">",prevstart,prevend)
            if prevstart < match.start():
                results.append(match.start())
        if len(results)==0:
            return -1
        else:
            print("[find_subarray]:",results)
            return results[0]

    def find_original_string_location(self, needles, haystack, prevstart, prevend):
        results = dict()
        for needle in needles:
            results[needle] = [hay for hay,elem in enumerate(haystack) if needle==elem]
            #print(needle, results[needle], prevstart)

        if len(results) == 0:
            return results
        #first = list(results.keys())[0]
        return results

    def detokenize(self, word_list):
        from nltk.tokenize.treebank import TreebankWordDetokenizer
        return TreebankWordDetokenizer().detokenize(word_list)

    def get_string(self):
        return self.string

    def get_location(self):
        return self.location

    def get_order(self):
        return self.ord

    def __eq__(self, other):
        if other == None:
            return False

        if self.string == other.get_string():
            if self.ord == other.get_order():
                if self.location == other.get_location():
                    return True
        return False

    def __str__(self):
        return self.detokenize([word.get_string() for word in self.words.values()])

    def __repr__(self):
        return self.detokenize([word.get_string() for word in self.words.values()])

class Word:
    def __init__(self, string, start_ind, end_ind):
        self.string = string
        self.start_location = start_ind
        self.end_location = end_ind
        #print("CREATE word:", string, start_ind, end_ind)

    def get_start_location(self):
        return self.start_location

    def get_end_location(self):
        return self.end_location

    def get_string(self):
        return self.string

    def __str__(self):
        return str(self.string + "(" + str(self.start_location) + ":" + str(self.end_location) + ")")

    def __repr__(self):
        return str(self.string + "(" + str(self.start_location) + ":" + str(self.end_location) + ")")
