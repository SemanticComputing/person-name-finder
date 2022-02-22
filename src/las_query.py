'''
Created on 17.2.2016

@author: Claire
'''
import urllib, codecs
from requests import Request, Session
import requests, json
import logging
import json
import traceback, sys, os
from flask import abort
import configparser
from configparser import Error, ParsingError, MissingSectionHeaderError, NoOptionError, DuplicateOptionError, DuplicateSectionError, NoSectionError

# logging setup
logging.config.fileConfig(fname='conf/logging.ini', disable_existing_loggers=False)
logger = logging.getLogger('las')

class lasQuery:
    def __init__(self, file_name_pattern="", path="", full_path="", url="", env='DEFAULT'):
        self.__file_name_pattern = file_name_pattern
        self.__path = path
        self.query_string_cache = dict()
        self.__url = url

        self.read_configs(env)

        logger.debug("Set url: %s", self.__url)

    def read_configs(self, env):

        try:
            config = configparser.ConfigParser()
            config.read('conf/config.ini')
            if env in config:
                self.read_env_config(config, env)
            elif env == None or len(env) == 0:
                err_msg = 'The environment is not set: %s' % (env)
                raise Exception(err_msg)
            else:
                if 'DEFAULT' in config:
                    self.read_env_config(config)
                else:
                    err_msg = 'Cannot find section headers: %s, %s' % (env, 'DEFAULT')
                    raise MissingSectionHeaderError(err_msg)
        except Error as e:
            logger.error("[ERROR] ConfigParser error: %s", sys.exc_info()[0])
            logger.error(traceback.print_exc())
            abort(500)
        except Exception as err:
            logger.error("[ERROR] Unexpected error: %s", sys.exc_info()[0])
            logger.error(traceback.print_exc())
            abort(500)

    def read_env_config(self, config, env='DEFAULT'):
        if 'las_url' in config[env]:
            self.__url = config[env]['las_url']
        else:
            logger.warning("Unable to find: las url in %s", config[env])

    def analysis(self, input, lookup_upos=None):
        res = " "
        j = self.morphological_analysis(input)
        reader = codecs.getreader("utf-8")
        print(j)
        for w in j:
            analysis = w['analysis']
            for r in analysis:
                wp = r['wordParts']
                for part in wp:
                    lemma = part['lemma']
                    upos=""
                    if 'tags' in part:
                        p = part['tags']
                        print(lemma, p)
                        if 'UPOS' in p:
                            p1 = p['UPOS']
                            if len(p1)>0:
                                upos = part['tags']['UPOS'][0]
                    if lookup_upos != None:
                        if upos.lower() == lookup_upos.lower():
                            res = res + lemma + " "
                    elif upos == 'NOUN' or upos == 'PROPN':
                        res = res + lemma + " "
        return res

    def title_analysis(self, input, lookup_upos=None, get_first=False):
        res = list()
        j = self.morphological_analysis(input)
        reader = codecs.getreader("utf-8")
        #print(j)
        for w in j:
            analysis = w['analysis']
            word = w['word']
            wid = 0
            #print("ANALYSIS FOR WORD:", word)
            lemma, upos = self.get_first_interpretation(analysis, lookup_upos)
            #print("AFTER ANALYSIS:",lemma, upos)
            if upos is not None:
                res.append((word, lemma, upos))

        return res

    def get_first_interpretation(self, analysis, lookup_upos):
        for r in analysis:
            wp = r['wordParts']
            for part in wp:
                lemma = part['lemma']
                upos = ""
                if 'tags' in part:
                    p = part['tags']
                    #print("TAGS:",lemma, p)
                    if 'UPOS' in p:
                        p1 = p['UPOS']
                        #print("P1:", p1)
                        if len(p1) > 0:
                            upos = part['tags']['UPOS'][0]
                            return lemma, upos
                        else:
                            return lemma, upos

        return None, None


    #morphological_analysis    
    def morphological_analysis(self,input):
        
        # do POST
        url = self.__url + '/analyze'
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        data = urllib.parse.urlencode(params).encode()
        
        content = None
        content = self.prepared_request_morphological(input)
        if content == None:
            return ""
        return content.json()
    
    def lexical_analysis(self,input, lang='fi'):
        result = ""

        # do POST
        url = self.__url + '/baseform'
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
        url = self.__url + '/baseform'
        params = {'text': input, 'locale' : lang}
        data = urllib.parse.urlencode(params).encode()
        req = Request('POST',url,headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            return resp
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: "  + str(ce))
        return None

    def prepared_request_morphological(self, input):
        s = Session()
        url = self.__url + '/analyze'
        params = {'text': input, 'locale':'fi', "forms":"V+N+Nom+Sg"}
        data = urllib.parse.urlencode(params).encode()
        req = Request('POST',url,headers={'X-Custom':'Test'},data=params)
        prepared = req.prepare()

        logger.info(prepared.headers)
        logger.info(prepared.body)

        try:
            resp = s.send(prepared)
            return resp
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: "  + str(ce))
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