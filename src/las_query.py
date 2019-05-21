'''
Created on 17.2.2016

@author: Claire
'''
import urllib, codecs
from requests import Request, Session
import requests, json
import logging
import json

# logging setup
logger = logging.getLogger('NamedEntity')
hdlr = logging.FileHandler('logs/namedentity.log')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

class lasQuery:
    def __init__(self, file_name_pattern="", path="", full_path=""):
        self.__file_name_pattern = file_name_pattern
        self.__path = path
        self.query_string_cache = dict()
        
    def analysis(self, input):
        res = " "
        j = self.morphological_analysis(input)
        reader = codecs.getreader("utf-8")

        for w in j:
            analysis = w['analysis']
            for r in analysis:
                wp = r['wordParts']
                for part in wp:
                    lemma = part['lemma']
                    upos=""
                    if 'tags' in part:
                        p = part['tags']
                        if 'UPOS' in p:
                            p1 = p['UPOS']
                            if len(p1)>0:
                                upos = part['tags']['UPOS'][0]
                    if upos == 'NOUN' or upos == 'PROPN':
                        res = res + lemma + " "
                
        return res

    #morphological_analysis    
    def morphological_analysis(self,input):
        
        # do POST
        url = 'http://demo.seco.tkk.fi/las/analyze'
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        data = urllib.parse.urlencode(params).encode()
        
        content =  None
        content = self.prepared_request_morphological(input)
        if content == None:
            return ""
        return content.json()
    
    def lexical_analysis(self,input, lang='fi'):
        result = ""

        # do POST
        url = 'http://demo.seco.tkk.fi/las/baseform'
        params = {'text': input, 'locale': lang}
        data = urllib.parse.urlencode(params).encode()

        if input not in self.query_string_cache.keys():
            content =  None
            content = self.prepared_request(input, lang)
            if content == None:
                return ""

            result = content.content.decode('utf-8')
            if result.startswith('"'):
                result = result[1:]
            if result.endswith('"'):
                result = result[:-1]

            # add to cache
            self.query_string_cache[input] = result
        else:
            result = self.query_string_cache[input]

        return result
    
    def prepared_request(self, input, lang):
        s = Session()
        url = 'http://demo.seco.tkk.fi/las/baseform'
        params = {'text': input, 'locale' : lang}
        data = urllib.parse.urlencode(params).encode()
        req = Request('POST','http://demo.seco.tkk.fi/las/baseform',headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            return resp
        except requests.ConnectionError as ce:
            print("Unable to open with native function. Error: "  + str(ce))
        return None
        
    def prepared_request_morphological(self, input):
        s = Session()
        url = 'http://demo.seco.tkk.fi/las/baseform'
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        data = urllib.parse.urlencode(params).encode()
        req = Request('POST','http://demo.seco.tkk.fi/las/analyze',headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            return resp
        except requests.ConnectionError as ce:
            print("Unable to open with native function. Error: "  + str(ce))
        return None
    
    def pretty_print_POST(self,req):
        """
        At this point it is completely built and ready
        to be fired; it is "prepared".
    
        However pay attention at the formatting used in 
        this function because it is programmed to be pretty 
        printed and may differ from the actual request.
        """
        print('{}\n{}\n{}\n\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
        ))