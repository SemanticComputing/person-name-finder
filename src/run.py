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
    text = ""
    if request.method == 'GET':
        text = request.args.get('text')
        input = {0:text}
        sentence_data, indeces = tokenization(text)
        #print("tokenization results",sentences)
        sentences, index_list = do_lemmatization(sentence_data, indeces)
        #print("data", input)
    elif request.method == "POST":
        if request.headers['Content-Type'] == 'text/plain' and len(request.data)>0:
            text = str(request.data.decode('utf-8'))
        elif 'text' in request.form:
            text = request.form['text']
        elif 'text' in request.args:
            text = request.args.get('text')
        elif 'Text' in request.headers:
            text = request.headers['Text']
        else:
            print("Unable to process the request! When using post, give param text using raw data or add it to form, url, or header.")
            print("Bad type", request.headers['Content-Type'])
            print("Missing data", request.data)
            print("Missing from header", request.headers)
            print("Missing from form", request.form)
            print("Missing from args", request.args)

        if len(text) > 0:
            sentence_data, indeces = tokenization(text)
            print("sentences dataset:", sentence_data)
            sentences, index_list = do_lemmatization(sentence_data, indeces)
            input = {0: str(request.data.decode('utf-8'))}
            print("data:", input)
            print("sentences:", sentences)
    else:
        print("This method is not yet supported:", request.method)
    return input, sentences, index_list

def setup_tokenizer():
    tokenizer = nltk.data.load('tokenizers/punkt/finnish.pickle')
    with open('data/abbreviations.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            print("Add abbreviation", row[0])
            tokenizer._params.abbrev_types.add(row[0])
    return tokenizer

def tokenization(text):
    result = list()
    structure = dict()
    counter = 0
    print('Tokenize this:', text)
    tokenizer = setup_tokenizer()
    sentences = tokenizer.tokenize(text)
    for sentence in sentences:
        splitted = re.split(r', |; | \(|\) | ja | tai ', sentence) #sentence.split('[,;]')

        if len(splitted) > 1:
            for chunk in splitted:
                result.append(chunk)
                if chunk not in structure:
                    structure[chunk] = counter
        else:
            result.append(sentence)
            if sentence not in structure:
                structure[sentence] = counter
        counter += 1

    print("Splitted:", result)
    return result, structure

def do_lemmatization(sentence_data, indeces):
    output = dict()
    index_lists = dict()
    for i in range(0, len(sentence_data)):
        output[i] = lemmatize(sentence_data[i])

        index_lists[i] = indeces[sentence_data[i]]
        print("Index list:", i, indeces[sentence_data[i]], sentence_data[i])


    #{i: lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
    return output, index_lists

def lemmatize(text):
    las = lasQuery()
    lemmatized = las.lexical_analysis(text, 'fi')
    print("Lemmatized:", lemmatized)
    return lemmatized

@app.route('/', methods=['POST', 'GET'])
def index():
    print("APP name",__name__)
    input_data, sentences, index_list = parse_input(request)
    print("DATA", sentences)
    if input_data != None:
        name_finder = NameFinder()
        results, code = name_finder.identify_name(sentences, index_list)

        if code == 1:
            print('results',results)
            data = {"status":200,"data":results}
            return json.dumps(data, ensure_ascii=False)
        else:
            data = {"status":-1,"Error":str(results)}
            return json.dumps(data, ensure_ascii=False)
    message = "<h3>Unable to process request</h3><p>Unable to retrieve results for text (%s).</p>" % str(request.args.get('text'))
    message += "<p>Please give parameters using GET or POST method. GET method example: <a href='http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper' target='_blank'>http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper</a></p>"+\
                    "POST method can be used by transmitting the parameters using url, header, or a form."
    return message


#if __name__ == '__main__':
#    app.run(debug=True,port=5000, host='0.0.0.0')