from src.sparqlqueries import SparqlQuries
import json
import string
from requests import Request, Session
import requests
import configparser
from configparser import Error, ParsingError, MissingSectionHeaderError, NoOptionError, DuplicateOptionError, DuplicateSectionError, NoSectionError
from collections import OrderedDict
from src.ambiguation_resolver import AmbiguityResolver
import sys, traceback
from flask import abort
from src.las_query import lasQuery
import logging
import logging.config


# logging setup
logging.config.fileConfig(fname='conf/logging.ini', disable_existing_loggers=False)
logger = logging.getLogger('namefinder')

class NameFinder:
    def __init__(self):
        self.last_names = dict()
        self.last_name_ind = dict()
        self.first_names = dict()
        self.first_name_ind = dict()

    def identify_name(self, env, sentence_chunk_strings, index_list, original_sentence_data, check_date=None, gender=False, title=False, date=False, word=False):
        logger.debug("Check titles? %s",title)
        names = dict()
        #results = list()
        all_names = list()
        resp = None
        for i,name_string in sentence_chunk_strings.items():
            self.last_names[i] = list()
            self.first_names[i] = list()
            logger.debug("Name: %s",name_string)

            dict_names, arr_names = self.split_names_to_arr(name_string, i)
            if len(arr_names) > 0:
                logger.debug("CHECK dates: %s, %s, %s", check_date, i, arr_names)
                checking_date = None
                #ind = i + 1
                if date is True and i in check_date:
                    checking_date = check_date[i]

                nr = NameRidler(dict_names, arr_names, name_string, env)

                name_list, resp = nr.get_names(check_for_dates=checking_date, gender=gender, titles=title, dates=date, word=word, fulltext=str(original_sentence_data[index_list[i]].get_sentence_string()), complete_list_of_name=all_names, env=env)
                logger.debug("Using index: %s", index_list[i])

                # parsing result
                if index_list[i] not in names.keys():
                    names[index_list[i]] = dict()
                    names[index_list[i]]["entities"] = list()
                names[index_list[i]]["entities"].extend(name_list)
                names[index_list[i]]["text"]=str(original_sentence_data[index_list[i]].get_sentence_string())
                names[index_list[i]]["sentence"] = str(index_list[i])
                all_names.extend(nr.get_full_name_entities())

        return list(names.values()), 1, resp

    def split_names_to_arr(self, name_string_obj, j):
        name_string = name_string_obj.get_lemma()
        logger.info("Process string: %s",name_string)
        names = name_string.split(" ")
        dict_names = dict()
        first_names = list()
        last_names = list()

        helper = list()
        binders = ['de', 'la', 'af', 'i', 'von', 'van', 'le', 'les', 'der', 'du', 'of', 'in', 'av']
        builder = ""
        prev = None
        next = None
        namecounter = 1
        last = len(names) -1

        for i in range(len(names)):
            s = names[i]
            table = str.maketrans({key: None for key in string.punctuation})
            name = s.translate(table)

            if i == 0:
                next = i + 1
                prev = None
            elif i == last:
                next = None
                prev = i - 1
            else:
                next = i + 1
                prev = i - 1

            if len(name) > 0:

                if name.lower() not in binders and len(builder) == 0 and name[0].isupper():
                    first_names.append(name)
                elif name.lower() in binders and len(builder) == 0:
                    builder = name
                elif len(builder) > 0 and (name.lower() in binders or name[0].isupper()):
                    builder = builder + " " + name
                else:
                    logger.info("Unable to identify name: %s", name)

                    if len(builder) > 0 and (name.lower() in binders or name[0].isupper()):
                        last_names.append(builder)
                    else:
                        if name[0].isupper():
                            prev_s = names[prev]
                            prev_name = prev_s.translate(table)
                            last_names.append(prev_name)

                    if len(first_names)>0 or len(last_names) >0:
                        dict_names[namecounter] = first_names + last_names
                        namecounter += 1

                    self.last_names[j].extend(last_names)
                    self.first_names[j].extend(first_names)

                    logger.debug("Names in dict: %s", dict_names)

                    first_names = list()
                    last_names = list()

        if len(first_names) > 0 or len(last_names) > 0:
            dict_names[namecounter] = first_names + last_names

        self.last_names[j].extend(last_names)
        self.first_names[j].extend(first_names)

        logger.debug("Names: %s, %s",self.first_names[j], self.last_names[j])
        logger.debug("Names in dict: %s", dict_names)

        return dict_names, self.first_names[j] + self.last_names[j]


class NameRidler:
    def __init__(self, dict_names, ordered_names, sentence_obj, env):
        self.sparql = SparqlQuries()
        self.full_name_entities = list()
        self.ord_names = ordered_names
        self.full_names = dict()
        self.full_name_lemmas = dict()
        self.gender_guess_url = ""
        self.gender_guess_threshold = 0.8
        self.regex_url = ""
        self.henko_endpoint = ""
        self.ord_full_names = dict()

        self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai )'
        self.contextual_chunking_single_separators = ['S', 'V']
        self.context_birth_identifiers = ['s.', 'syntynyt']
        self.context_death_identifiers = ['k.', 'kuollut']
        self.context_lifespan_separators = ['-', '–']

        # configure
        self.read_configs(env)

        # query and parse
        names = self.sparql.query_names(dict_names, endpoint=self.henko_endpoint)
        self.parse(names, sentence_obj)

        # disambiguate
        self.ambiguity_identifier = AmbiguityResolver()

    def get_full_name_entities(self):
        return self.full_name_entities

    def get_full_names(self):
        return self.full_names

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
        if 'henko_endpoint' in config[env]:
            self.henko_endpoint = config[env]['henko_endpoint']
        else:
            logger.warnning("Unable to find: henko_endpoint in %s", config[env])
            #self.henko_endpoint = "http://ldf.fi/henko/sparql"

        if 'gender_guess_url' in config[env]:
            self.gender_guess_url = config[env]['gender_guess_url']
        else:
            logger.warnning("Unable to find: gender_guess_url in %s", config[env])
            #self.gender_guess_url = "http://nlp.ldf.fi/gender-guess"

        if 'gender_guess_threshold' in config[env]:
            self.gender_guess_threshold = float(config[env]['gender_guess_threshold'])
        else:
            logger.warnning("Unable to find: gender_guess_threshold in %s", config['DEFAULT'])
            #self.gender_guess_threshold = 0.8

        if 'regex_url' in config[env]:
            self.regex_url = config[env]['regex_url']
        else:
            logger.warnning("Unable to find: regex_url in %s", config[env])
            #self.regex_url = "http://nlp.ldf.fi/regex"

        if 'string_chunking_pattern' in config[env]:
            self.string_chunking_pattern = config[env]['string_chunking_pattern'].split(',')
        else:
            logger.warnning("Unable to find: string_chunking_pattern in %s", config[env])
            self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai )'

    # render data into result format
    def get_names(self, check_for_dates=None, gender=False, titles=False, dates=False, word=False, fulltext=None, complete_list_of_name=None, env='DEFAULT'):
        responses = dict()
        entities = list()
        fullnames = list()

        # disambiguate
        self.ambiguity_identifier.set_full_name(complete_list_of_name)
        self.ambiguity_identifier.ambiguity_solver()
        ambiguous = self.ambiguity_identifier.get_ambiguous_names()

        prev_entity = None
        for name, arr in self.full_names.items():
            entity = dict()
            items = list()
            str_name = name.split('_')[0].strip()
            if len(str_name) > 0:
                entity['full_name'] = str_name
                entity['full_name_lemma'] = self.full_name_lemmas[str_name]

                # add ambiguity information
                if name in ambiguous.keys():
                    if ambiguous[name].get_place_ambiguity():
                        entity['ambigous_place'] = ambiguous[name].get_place_ambiguity()
                    if ambiguous[name].get_vocation_ambiguity():
                        entity['ambigous_vocation'] = ambiguous[name].get_vocation_ambiguity()

                check_name_i = max(list(self.ord_full_names.keys()))
                check_name = self.ord_full_names[check_name_i].strip()
                if gender:
                    entity['gender'], resp = self.guess_gender(str_name)
                    responses[name.strip()] = resp
                if check_for_dates != None and dates is True and check_name == str_name:
                    output,resp = self.query_dates(check_for_dates)
                    date_type = self.check_string_start(check_for_dates)
                    if date_type > 0:
                        counter = 0
                        for item in output[check_for_dates]:
                            if '–' in item[0] or '-' in item[0]:
                                entity['lifespan_time'] = item[0]
                            else:
                                if counter == 0:
                                    entity['birth_date'] = item[0]
                                else:
                                    entity['death_date'] = item[0]
                if titles and fulltext != None:
                    logger.debug("TITLE CHECK")
                    title = self.find_title(fulltext, str_name, env)
                    entity['titles'] = list()
                    entity['titles'].append(title)
                for item in arr:
                    if item.get_json() not in items:
                        logger.debug("Item: %s", item)
                        items.append(item.get_json())

                entity['names'] = items
                entities.append(entity)
                prev_entity = entity

        logger.debug("entities %s", entities)
        return entities, responses

    def check_string_start(self, string):
        birth = ['s.', 'syntynyt']
        death = ['k.', 'kuollut']
        for b in self.context_birth_identifiers:
            if string.startswith(b):
                return 1
        for d in self.context_death_identifiers:
            if string.startswith(d):
                return 2
        splitted = string.split()
        if splitted[0].isdigit():
            return 3

        splitted = string.split('–')
        if splitted[0].isdigit():
            return 3

        splitted = string.split('-')
        if splitted[0].isdigit():
            return 3

        return 0

    def combine_entity_lists(self, newlist, oldlist):
        for entity in newlist:
            if entity not in oldlist:
                oldlist.append(entity)

        return oldlist

    def parse(self, queried_names, sentence_obj):
        arr = dict()
        helper_arr = OrderedDict()
        qn_helper = dict()
        name_links = dict()
        counter = 0
        full_name_counter = 0
        label = ""
        prev = None
        name = None
        full_name = ""
        prev_names =list()
        string_start = -1
        string_end = -1
        prev_string_start = -1
        for ind, rs in queried_names.items():
            rs_queried_name = rs.get_resultset()
            counter = 1
            for i, queried_name in rs_queried_name.items():
                logger.info("%s, %s",i, queried_name)
                if string_start != None:
                    prev_string_start = string_start

                for result in queried_name:

                    prev = name
                    prev_names.append(label)
                    uri = str(result.get_uri())
                    label = str(result.get_label())
                    count = int(result.get_count())
                    type = str(result.get_type())
                    linkage = str(result.get_linkage())
                    place = result.get_ref_place()
                    vocation = result.get_ref_vocation()
                    logger.debug("%s, %s, %s, %s, %s",result, counter, prev, name, result.get_ref_place())
                    logger.debug("P/V: %s, %s",str(place), vocation)

                    if counter == 0:
                        counter += 1
                    elif prev != None:
                        if prev.get_name() != label:
                            #print("Raising counter:", prev.get_name(), label, counter, string_start,prev_string_start)
                            counter += 1
                            if string_start != None:
                                prev_string_start = string_start
                            else:
                                logger.info("string start none x.x: %s", prev_string_start)
                        else:
                            logger.info("Not raising counter: %s, %s", prev.get_name(), label)

                    string_start, string_end = sentence_obj.find_name_location(label, prev_string_start, string_end)
                    if string_start == None:
                        logger.info("String start none: %s, %s, %s, %s, %s, %s", label, uri, type, linkage, prev_string_start, string_end)
                    original_form = sentence_obj.find_from_text(string_start, string_end)

                    if string_end != None and string_start != None and original_form != None:

                        if prev != None:
                            if (prev.get_type() == "Sukunimi" and type == "Etunimi") and \
                                    (prev.get_name().strip() != label.strip() and len(list(arr.keys()))>1) and (prev.get_string_end()<=string_start-2) and \
                                    (prev.get_name_lemma() != prev.get_name() or original_form != label.strip()):
                                counter = 1
                                logger.info("Adding a last name: %s (%s)", prev.get_type(), type)
                                logger.info("Adding a last name: %s, %s", prev.get_name().strip(), label.strip())
                                logger.info("Adding a last name: %s",str(len(list(arr.keys()))>1))
                                logger.info("Adding a last name: %s, %s", prev.get_string_end(),string_start-2)

                                arr, full_name, full_name_counter, full_name_lemma, helper_arr, name = self.extract_name(
                                    arr,
                                    full_name_counter,
                                    helper_arr, name,{label:queried_name})


                            if prev != None:
                                if label != prev.get_name():
                                    full_name += label + " "

                        logger.info("Add name: label=%s, original_form=%s, count=%s, type=%s, counter=%s, uri=%s, link=%s, start=%s", label, original_form, count, type, counter, uri, linkage, string_start)
                        name = Name(label, original_form, count, type, counter, uri, linkage, string_start, place, vocation)

                        if counter not in helper_arr.keys():
                            helper_arr[counter] = list()
                        if name not in helper_arr[counter]:
                            helper_arr[counter].append(name)

                        if label not in arr.keys():
                            arr[label] = list()
                        if name not in arr[label]:
                            arr[label].append(name)

                        if label not in qn_helper.keys():
                            qn_helper[label] = queried_name
                        else:
                            for item in queried_name:
                                if item not in qn_helper[item.get_label()]:
                                    qn_helper[label].append(item)

            logger.debug("%s, %s, %s, %s, %s",arr, full_name_counter, helper_arr, name, queried_name)
            arr, full_name, full_name_counter, full_name_lemma, helper_arr, name = self.extract_name(arr,
                                                                                                     full_name_counter,
                                                                                                     helper_arr, name,qn_helper)
            logger.debug("%s, %s, %s, %s, %s, %s",arr, full_name, full_name_counter, full_name_lemma, helper_arr, name)

    # def ambiguity_solver(self, names, str_full_name_lemma):
    #     last_name = None
    #     for name_id, arr_names in self.full_names:
    #         str_name = name_id.split('_')[0].strip()
    #         if str_full_name_lemma != self.full_name_lemmas[str_name]:
    #             pass

    def extract_name(self, arr, full_name_counter, helper_arr, name, alternatives):
        argh, full_name, full_name_lemma = self.determine_name(arr, helper_arr, alternatives)

        logger.debug("[extract_name] Full name: %s %s %s", full_name, argh, full_name_counter)
        fullname_ind = full_name + "_" + str(full_name_counter)

        full_name_entity = FullName(full_name_counter, full_name, full_name_lemma, argh)
        self.full_name_entities.append(full_name_entity)

        self.full_names[fullname_ind] = argh
        self.full_name_lemmas[full_name] = full_name_lemma
        self.ord_full_names[full_name_counter] = full_name
        full_name_counter += 1

        arr = dict()
        helper_arr = dict()
        prev = None
        name = None
        full_name = ""
        return arr, full_name, full_name_counter, full_name_lemma, helper_arr, name

    def determine_name(self, names, helper, alternatives):
        logger.debug("[determine_name]: ...")
        family_names = list()
        first_names = list()
        last = len(helper)
        full_name = ""
        prev = None
        name_unidentified = False

        for loc, names in helper.items():
            for name in names:
                if prev != None:
                    if name_unidentified == True:
                        name_unidentified = False
                        if prev.get_type() == "Sukunimi":
                            family_names.append(prev)
                            name_unidentified = False
                        elif prev.get_type() == "Etunimi":
                            first_names.append(prev)
                            name_unidentified = False
                        else:
                            logger.info("Cannot add, %s", prev)
                logger.debug("Before crash: %s, %s",alternatives, name.get_name())
                if self.is_family_name(name, last, alternatives[name.get_name_lemma()]) and not(self.is_first_name(name, last)):
                    if name not in family_names:
                        family_names.append(name)
                        prev = name
                        name_unidentified = False
                elif self.is_first_name(name, last) and not(self.is_family_name(name, last, alternatives[name.get_name_lemma()])):
                    if name not in first_names:
                        first_names.append(name)
                        prev = name
                        name_unidentified = False
                else:
                    if name.get_type() == "Sukunimi" and name.get_location() > 1 and not(self.is_first_name(name, last)):
                        family_names.append(name)
                        prev = name
                        name_unidentified = False
                    else:
                        logger.warning("Unable to identify name --> %s %s %s", name, last, helper)
                        name_unidentified = True
                        prev = name

        if prev != None:
            if name_unidentified == True:
                name_unidentified = False
                if prev.get_type() == "Sukunimi":
                    family_names.append(prev)
                    name_unidentified = False
                elif prev.get_type() == "Etunimi":
                    first_names.append(prev)
                    name_unidentified = False
                else:
                    logger.warning("Cannot add, %s", prev)

        fnames = [fn.get_name() for fn in first_names]
        lnames = [fn.get_name() for fn in family_names]

        overlap = set(fnames).intersection(set(lnames))

        if len(overlap) > 0:
            logger.debug("Overlapping names: %s", overlap)
            for o in overlap:
                logger.debug("Before, check last: %s, %s, %s", last, helper, names)
                first_names, family_names = self.reduce_overlapping(o, first_names, family_names, last, alternatives)

        logger.debug("Return names: %s", first_names + family_names)

        full = first_names + family_names
        full_name_lemma = ' '.join(str(e.get_name_lemma()) for e in full)
        full_name = ' '.join(str(e.get_name()) for e in full)
        return full, full_name, full_name_lemma

    def reduce_overlapping(self, label, fnames, lnames, last, alternatives):
        # compare two names: fname and lname
        if fnames != None and lnames != None:
            fname = self.find_name(fnames, label)
            lname = self.find_name(lnames, label)

            logger.debug("%s, %s", fname, lname)

            l_last = len(lnames)-1
            f_last = len(fnames)-1

            if fname != None and lname != None:
                if fname == lname:
                    if fname.get_link() != lname.get_link():
                        lname.add_link(fname.get_link())
                    elif fname.get_link() != lname.get_link():
                        fname.add_link(lname.get_link())
                if fname.get_location() == lname.get_location() and self.is_family_name(lname, last, alternatives[lname.get_name_lemma()]) and not(self.is_first_name(fname, last)):
                    fnames.remove(fname)
                elif fname.get_location() == lname.get_location() and not(self.is_family_name(lname, last, alternatives[lname.get_name_lemma()])) and self.is_first_name(fname, last):
                    lnames.remove(lname)
                elif fname.get_location() == lname.get_location() and self.is_family_name(lname, last, alternatives[lname.get_name_lemma()]) and self.is_first_name(fname, last):
                    if fname.get_count() > lname.get_count():
                        lnames.remove(lname)
                    elif fname.get_count() < lname.get_count():
                        fnames.remove(fname)
                else:
                    prob_A = fname.get_count()
                    prob_B = lname.get_count()
                    logger.info("Probability that it is a first name: %s", fname.get_count())
                    logger.info("Label: %s", label)
                    logger.info("Locations: %s, %s", fname.get_location(), lname.get_location())
                    logger.info("Is family name? %s", self.is_family_name(lname, last, alternatives[lname.get_name_lemma()]))
                    logger.info("Is first name? %s", self.is_first_name(fname, last))
            else:
                if lname == None:
                    logger.warnning("Unable to find label from lastnames: %s, %s", label, lnames)
                if fname == None:
                    logger.warnning("Unable to find label from firstnames: %s, %s", label, fnames)

            fnames.sort(key=lambda x: x.get_string_start(), reverse=False)
            lnames.sort(key=lambda x: x.get_string_start(), reverse=False)
            #lname_list = sorted(lnames, key=lambda x: x.string_start, reverse=False)

            return fnames, lnames

    def find_name(self, arr, label):
        for item in arr:
            logger.debug("Search for label %s from item %s", label, item)
            if item.get_name().strip() == label.strip():
                return item

        return None

    def is_family_name(self, name, last, alternatives):
        logger.debug("Is lastname? %s, %s, %s", name, last, alternatives)
        other_types = [a.get_type() for a in alternatives if a.get_type() != name.get_type()]
        if name.get_type() == "Sukunimi" and name.get_location() == last:
            return True
        elif name.get_type() == "Sukunimi" and len(other_types) < 1:
            logger.debug("Others: %s", other_types)
            return True
        return False

    def is_first_name(self, name, last):
        logger.debug("Location of first: %s, %s, %s, %s", last, name.get_location(), name.get_type(), name)
        if name.get_type() == "Etunimi" and ((last == 1 or name.get_location() < last) and name.get_location() < 5):
            return True
        else:
            if name.get_type() != "Etunimi":
                logger.info("Not a first name: Type FAIL")
            if (last != 1 or name.get_location() > last):
                logger.info("Not a first name: location and last FAIL")
            if name.get_location() >= 5:
                logger.info("Not a first name: Too long, FAIL")
        return False

    def guess_gender(self, name):

        import requests
        import logging

        # These two lines enable debugging at httplib level (requests->urllib3->http.client)
        # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
        # The only thing missing will be the response.body which is not logged.
        try:
            import http.client as http_client
        except ImportError:
            # Python 2
            import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        #s = Session()
        data = None

        # api-endpoint
        URL = self.gender_guess_url
        #URL = "http://gender-guess.nlp.ldf.fi/"

        # defining a params dict for the parameters to be sent to the API
        params = {'name': name, 'threshold': self.gender_guess_threshold}

        # header
        headers = {'content-type': 'application/json'}

        resp = requests.get(URL, params=params, headers=headers, stream=True)

        try:
            if resp != None:
                logger.info("Request parameters: %s", params)
                logger.info("Response status: %s", resp.status_code)
                logger.info("RESPONSE header: %s", resp.headers)
                logger.info("RESPONSE raw: %s", resp.raw)
                logger.info("RESPONSE content: %s", resp.content)
                logger.info("RESPONSE request URL: %s", resp.url)
            else:
                logger.info("Raw response")
            data = resp.json()
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: %s" + str(ce))
        except Exception as e:
            if resp != None:
                logger.error("Unable to process a request: %s, %s", resp, resp.text)
                return "Unknown", resp
            logger.error(e)

            return "Unknown", resp

        logger.info(data)

        if 'gender' in data['results']:
            return data['results']['gender'], resp
        else:
            return "Unknown", resp

    def query_dates(self, string):

        logger.debug("CHECK DATE")

        import requests
        import logging

        # These two lines enable debugging at httplib level (requests->urllib3->http.client)
        # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
        # The only thing missing will be the response.body which is not logged.
        try:
            import http.client as http_client
        except ImportError:
            # Python 2
            import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        data = None

        # api-endpoint
        URL = self.regex_url

        # defining a params dict for the parameters to be sent to the API
        params = {'text': string}

        # header
        headers = {'content-type': 'application/json'}

        resp = requests.get(URL, params=params, headers=headers, stream=True)

        try:
            if resp != None:
                logger.info("Request parameters: %s", params)
                logger.info("Response status: %s", resp.status_code)
                logger.info("RESPONSE header: %s", resp.headers)
                logger.info("RESPONSE raw: %s", resp.raw)
                logger.info("RESPONSE content: %s", resp.content)
                logger.info("RESPONSE request URL: %s", resp.url)
            else:
                logger.info("Raw response")
            resultset = resp.json()
            data = None
            if resultset['status'] == 200:
                data = resultset['data']
        except requests.ConnectionError as ce:
            logger.error("Unable to open with native function. Error: %s", str(ce))
        except Exception as e:
            if resp != None:
                logger.error("Unable to process a request: %s %s", resp, resp.text)
            logger.error(e)

            return "Unknown 2", resp

        logger.debug("DATA: %s",data)
        results = dict()

        if data != None:
            for key,item in data.items():
                logger.debug('Item: %s',item)
                for i in item['entities']:
                    if 'category' in i and 'entity' in i:
                        if i['category'] == 'DATETIME':
                            start = i['start_index']
                            end = i['end_index']
                            if 'string' not in results:
                                results[string] = list()
                            results[string].append((i['entity'], start, end))
                        else:
                            logger.info("Wrong type: %s", item['entities'])
                else:
                    logger.info("Unable to find entity in results:" %s, item['entities'])

        return results, resp

    def find_title(self, string, name, env):
        las = lasQuery(env)
        lookup = string.split(name)[0].strip()
        print(lookup)
        if len(lookup) > 0:
            word_before_name = ""
            if ' ' in lookup:
                word_before_name = lookup.split(' ')[-1]
            else:
                word_before_name = lookup
            logger.debug("From string: [%s], %s" % (lookup, lookup.split(' ')))
            logger.debug("Check string: %s", word_before_name)
            result = self.find_noun_before_name(string, name, env) #las.analysis(input=lookup, lookup_upos='NOUN')
            logger.debug("ANALYSIS RESULT: %s",result)
            return result.strip()
        else:
            logger.info("Cannot find title")

    def find_noun_before_name(self, string, name, env):
        UPOS = 2
        LEMMA = 1
        WORD = 0
        las = lasQuery(env)
        result = las.title_analysis(input=string, lookup_upos='NOUN')
        lookup = string.split(name)[0].strip()
        if len(lookup) > 0:
            word_before_name = ""
            if ' ' in lookup:
                word_before_name = lookup.split(' ')[-1]
            else:
                word_before_name = lookup
        index = lookup.split(' ').index(word_before_name)
        try:
            tpl = result[index]
            if tpl[UPOS] == 'NOUN':
                return tpl[LEMMA]
            else:
                print("Wrong type", tpl[UPOS])
                print("For word", tpl[WORD])
        except Exception as err:
            print(err)
            print("RESULT:",result, index)
            print("LOOKUP:", lookup, word_before_name, index)
            print("STRING:",string)
            print("NAME:", name)

        return ""

class FullName:
    def __init__(self, ind, full_name, full_name_lemma, full_name_entities):
        self.id = ind
        self.full_name = full_name
        self.full_name_lemma = full_name_lemma
        self.full_name_entities = full_name_entities
        self.place_ambiguity = None
        self.vocation_ambiguity = None

    def get_full_name(self):
        return self.full_name

    def get_full_name_lemma(self):
        return self.full_name_lemma

    def get_full_name_entities(self):
        return self.full_name_entities

    def get_full_name_index(self):
        return self.full_name + "_" + str(self.id)

    def get_place_ambiguity(self):
        return self.place_ambiguity

    def set_place_ambiguity(self, value):
        if value != None:
            self.place_ambiguity = value

    def get_vocation_ambiguity(self):
        return self.vocation_ambiguity

    def set_vocation_ambiguity(self, value):
        if value != None:
            self.vocation_ambiguity = value

    def get_json(self):
        return {'name':str(self.original_form), 'lemma':str(self.label), 'type':str(self.clarify_type()), 'location':str(self.location), 'uri':self.name_uri, 'start_ind':self.string_start, 'end_ind':self.string_end}

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return self.full_name

    def __eq__(self, other):
        if other != None:
            if self.get_name() == other.get_name():
                if self.get_type() == other.get_type():
                    if self.get_location() == other.get_location():
                        return True
        return False

class Name:
    def __init__(self, label, original_form, count, type, location, name_uri, linkage, string_start, place=None, vocation=None):
        self.label = label
        self.original_form = original_form
        self.count = count
        self.type = type
        self.location = location
        self.name_uri = name_uri
        self.linkage = list()
        self.linkage.append(linkage)
        self.string_start = string_start
        self.string_end = self.string_start + len(self.label)
        self.ref_place = place
        self.ref_vocation = vocation
        #print("place:"+str(place))

    def get_link(self):
        return self.linkage

    def get_name(self):
        return self.original_form

    def get_name_lemma(self):
        return self.label

    def get_type(self):
        return self.type

    def get_location(self):
        return self.location

    def get_count(self):
        return self.count

    def get_string_start(self):
        return self.string_start

    def get_string_end(self):
        return self.string_end

    def get_ref_vocation(self):
        return self.ref_vocation

    def get_ref_place(self):
        return self.ref_place

    def add_link(self, link):
        if link not in self.linkage:
            self.linkage.append(link)

    def clarify_type(self, lang='fi'):
        if self.type == "Sukunimi":
            if lang == 'fi':
                return "Sukunimi"
            else:
                return "Last name"
        if self.type == "Etunimi":
            if lang == 'fi':
                return "Etunimi"
            else:
                return "First name"
        return self.type

    def if_names_related(self, other):
        if other != None:
            if self.get_name() == other.get_name():
                if self.get_type() == other.get_type():
                    return True
        return False


    def get_json(self):
        return {'name':str(self.original_form), 'lemma':str(self.label), 'type':str(self.clarify_type()), 'location':str(self.location), 'uri':self.linkage[0], 'start_ind':self.string_start, 'end_ind':self.string_end}

    def __str__(self):
        return self.label + " (" + str(self.count) + "): " + self.type + " @ " + str(self.location)

    def __repr__(self):
        return self.label + " (" + str(self.count) + "): " + self.type + " @ " + str(self.location)

    def __eq__(self, other):
        if other != None:
            if self.get_name() == other.get_name():
                if self.get_type() == other.get_type():
                    if self.get_location() == other.get_location():
                        return True
        return False



