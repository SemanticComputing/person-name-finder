from flask import Flask
from flask import request
import argparse
import sys, os
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

app = Flask(__name__)

@app.before_request
def before_request():
    if True:
        print("HEADERS", request.headers)
        print("REQ_path", request.path)
        print("ARGS",request.args)
        print("DATA",request.data)
        print("FORM",request.form)

def parse_input(request):
    input = None
    sentences = None
    if request.method == 'GET':
        text = request.args.get('text')
        input = {0:text}
        sentence_data = tokenization(text)
        #print("tokenization results",sentences)
        sentences = {i: lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
        #print("data", input)
    else:
        if request.headers['Content-Type'] == 'text/plain':
            sentence_data = tokenization(str(request.data.decode('utf-8')))
            print("sentences dataset:", sentence_data)
            sentences = {i:lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
            input = {0:str(request.data.decode('utf-8'))}
            print("data:", input)
            print("sentences:", sentences)
        else:
            print("Bad type", request.headers['Content-Type'])
    return input, sentences

def setup_tokenizer():
    tokenizer = nltk.data.load('tokenizers/punkt/finnish.pickle')
    with open('data/abbreviations.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            print("Add abbreviation", row[0])
            tokenizer._params.abbrev_types.add(row[0])
    return tokenizer

def tokenization(text):
    print('Tokenize this:', text)
    tokenizer = setup_tokenizer()
    return tokenizer.tokenize(text)

def lemmatize(text):
    las = lasQuery()
    lemmatized = las.lexical_analysis(text, 'fi')
    print("Lemmatized:", lemmatized)
    return lemmatized

@app.route('/', methods=['POST', 'GET'])
def index():
    print("APP name",__name__)
    input_data, sentences = parse_input(request)
    print("DATA", sentences)
    if input_data != None:
        name_finder = NameFinder()
        results, code = name_finder.identify_name(sentences)

        if code == 1:
            print('results',results)
            data = {"status":200,"data":str(results)}
            return json.dumps(data, ensure_ascii=False)
        else:
            data = {"status":-1,"Error":str(results)}
            return json.dumps(data, ensure_ascii=False)
    return "415 Unsupported Media Type ;)"


#if __name__ == '__main__':
#    app.run(debug=True,port=5000, host='0.0.0.0')
