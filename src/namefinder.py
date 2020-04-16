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

class NameFinder:
    def __init__(self):
        self.last_names = dict()
        self.last_name_ind = dict()
        self.first_names = dict()
        self.first_name_ind = dict()

    def identify_name(self, env, sentence_chunk_strings, index_list, original_sentence_data, check_date=None, gender=False, title=False, date=False, word=False):
        names = dict()
        resp = None
        for i,name_string in sentence_chunk_strings.items():
            self.last_names[i] = list()
            self.first_names[i] = list()
            print("Name:",name_string)

            dict_names, arr_names = self.split_names_to_arr(name_string, i)
            if len(arr_names) > 0:
                #print("CHECK dates:", check_date, i, arr_names)
                checking_date = None
                #ind = i + 1
                if date is True and i in check_date:
                    checking_date = check_date[i]

                nr = NameRidler(dict_names, arr_names, name_string, env)
                name_list, resp = nr.get_names(check_for_dates=checking_date, gender=gender, titles=title, dates=date, word=word)
                print("Using index:", index_list[i])

                # parsing result
                if index_list[i] not in names.keys():
                    names[index_list[i]] = dict()
                    names[index_list[i]]["entities"] = list()
                names[index_list[i]]["entities"].extend(name_list)
                names[index_list[i]]["sentence"]=str(original_sentence_data[index_list[i]].get_sentence_string())

        return names, 1, resp

    def split_names_to_arr(self, name_string_obj, j):
        name_string = name_string_obj.get_lemma()
        #print("Process string:",name_string)
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
                    print("Unable to identify name:", name)

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

                    #print("Names in dict:", dict_names)

                    first_names = list()
                    last_names = list()

        if len(first_names) > 0 or len(last_names) > 0:
            dict_names[namecounter] = first_names + last_names

        self.last_names[j].extend(last_names)
        self.first_names[j].extend(first_names)

        print("Names:",self.first_names[j], self.last_names[j])
        print("Names in dict:", dict_names)

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
        print(names)
        self.parse(names, sentence_obj)

        # disambiguate
        self.ambiguity_identifier = AmbiguityResolver()

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
            print("[ERROR] ConfigParser error:", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)
        except Exception as err:
            print("[ERROR] Unexpected error:", sys.exc_info()[0])
            traceback.print_exc()
            abort(500)

    def read_env_config(self, config, env='DEFAULT'):
        if 'henko_endpoint' in config[env]:
            self.henko_endpoint = config[env]['henko_endpoint']
        else:
            print("Unable to find: henko_endpoint in ", config[env])
            #self.henko_endpoint = "http://ldf.fi/henko/sparql"

        if 'gender_guess_url' in config[env]:
            self.gender_guess_url = config[env]['gender_guess_url']
        else:
            print("Unable to find: gender_guess_url in ", config[env])
            #self.gender_guess_url = "http://nlp.ldf.fi/gender-guess"

        if 'gender_guess_threshold' in config[env]:
            self.gender_guess_threshold = float(config[env]['gender_guess_threshold'])
        else:
            print("Unable to find: gender_guess_threshold in ", config['DEFAULT'])
            #self.gender_guess_threshold = 0.8

        if 'regex_url' in config[env]:
            self.regex_url = config[env]['regex_url']
        else:
            print("Unable to find: regex_url in ", config[env])
            #self.regex_url = "http://nlp.ldf.fi/regex"

        if 'string_chunking_pattern' in config[env]:
            self.string_chunking_pattern = config[env]['string_chunking_pattern'].split(',')
        else:
            print("Unable to find: string_chunking_pattern in ", config[env])
            self.string_chunking_pattern = r'(, |; | \(|\)| ja | tai )'

    # render data into result format
    def get_names(self, check_for_dates=None, gender=False, titles=False, dates=False, word=False):
        responses = dict()
        entities = list()

        # disambiguate
        self.ambiguity_identifier.set_full_name(self.full_name_entities)
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
                for item in arr:
                    if item.get_json() not in items:
                        #print("Item:", item)
                        items.append(item.get_json())

                entity['names'] = items
                entities.append(entity)
                prev_entity = entity

        print("entities", entities)
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
                    print(result, counter, prev, name, result.get_ref_place())
                    print("P/V:",str(place), vocation)

                    if counter == 0:
                        counter += 1
                    elif prev != None:
                        if prev.get_name() != label:
                            print("Raising counter:", prev.get_name(), label, counter, string_start,prev_string_start)
                            counter += 1
                            if string_start != None:
                                prev_string_start = string_start
                            else:
                                print("string start none x.x", prev_string_start)
                        else:
                            print("Not raising counter:", prev.get_name(), label)

                    string_start, string_end = sentence_obj.find_name_location(label, prev_string_start, string_end)
                    if string_start == None:
                        print("String start none:", label, uri, type, linkage, prev_string_start, string_end)
                    original_form = sentence_obj.find_from_text(string_start, string_end)

                    if string_end != None and string_start != None and original_form != None:

                        if prev != None:
                            if (prev.get_type() == "Sukunimi" and type == "Etunimi") and \
                                    (prev.get_name().strip() != label.strip() and len(list(arr.keys()))>1) and (prev.get_string_end()<=string_start-2) and \
                                    (prev.get_name_lemma() != prev.get_name() or original_form != label.strip()):
                                counter = 1
                                print("Adding a last name:", prev.get_type(), type)
                                print("Adding a last name:", prev.get_name().strip(), label.strip())
                                print("Adding a last name:",len(list(arr.keys()))>1)
                                print("Adding a last name:", prev.get_string_end(),string_start-2)

                                arr, full_name, full_name_counter, full_name_lemma, helper_arr, name = self.extract_name(
                                    arr,
                                    full_name_counter,
                                    helper_arr, name,queried_name)


                            if prev != None:
                                if label != prev.get_name():
                                    full_name += label + " "

                        print("Add name:", label, original_form, count, type, counter, uri, linkage, string_start)
                        name = Name(label, original_form, count, type, counter, uri, linkage, string_start, place, vocation)

                        if counter not in helper_arr.keys():
                            helper_arr[counter] = list()
                        if name not in helper_arr[counter]:
                            helper_arr[counter].append(name)

                        if label not in arr.keys():
                            arr[label] = list()
                        if name not in arr[label]:
                            arr[label].append(name)

            print(arr, full_name_counter, helper_arr, name, queried_name)
            arr, full_name, full_name_counter, full_name_lemma, helper_arr, name = self.extract_name(arr,
                                                                                                     full_name_counter,
                                                                                                     helper_arr, name,queried_name)
            print(arr, full_name, full_name_counter, full_name_lemma, helper_arr, name)

    def ambiguity_solver(self, names, str_full_name_lemma):
        last_name = None
        for name_id, arr_names in self.full_names:
            str_name = name_id.split('_')[0].strip()
            if str_full_name_lemma != self.full_name_lemmas[str_name]:
                pass


    def extract_name(self, arr, full_name_counter, helper_arr, name, alternatives):
        argh, full_name, full_name_lemma = self.determine_name(arr, helper_arr, alternatives)

        print("Full name:", full_name, argh, full_name_counter)
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
                            print("Cannot add,", prev)

                if self.is_family_name(name, last, alternatives) and not(self.is_first_name(name, last)):
                    if name not in family_names:
                        family_names.append(name)
                        prev = name
                        name_unidentified = False
                elif self.is_first_name(name, last) and not(self.is_family_name(name, last, alternatives)):
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
                        print("Unable to identify name --> ", name, last, helper)
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
                    print("Cannot add,", prev)

        fnames = [fn.get_name() for fn in first_names]
        lnames = [fn.get_name() for fn in family_names]

        overlap = set(fnames).intersection(set(lnames))

        if len(overlap) > 0:
            #print("Overlapping names:", overlap)
            for o in overlap:
                #print("Before, check last", last, helper, names)
                first_names, family_names = self.reduce_overlapping(o, first_names, family_names, last, alternatives)

        #print("Return names:", first_names + family_names)

        full = first_names + family_names
        full_name_lemma = ' '.join(str(e.get_name_lemma()) for e in full)
        full_name = ' '.join(str(e.get_name()) for e in full)
        return full, full_name, full_name_lemma

    def reduce_overlapping(self, label, fnames, lnames, last, alternatives):
        # compare two names: fname and lname
        if fnames != None and lnames != None:
            fname = self.find_name(fnames, label)
            lname = self.find_name(lnames, label)

            #print(fname, lname)

            l_last = len(lnames)-1
            f_last = len(fnames)-1

            if fname != None and lname != None:
                if fname == lname:
                    if fname.get_link() != lname.get_link():
                        lname.add_link(fname.get_link())
                    elif fname.get_link() != lname.get_link():
                        fname.add_link(lname.get_link())
                if fname.get_location() == lname.get_location() and self.is_family_name(lname, last, alternatives) and not(self.is_first_name(fname, last)):
                    fnames.remove(fname)
                elif fname.get_location() == lname.get_location() and not(self.is_family_name(lname, last, alternatives)) and self.is_first_name(fname, last):
                    lnames.remove(lname)
                elif fname.get_location() == lname.get_location() and self.is_family_name(lname, last, alternatives) and self.is_first_name(fname, last):
                    if fname.get_count() > lname.get_count():
                        lnames.remove(lname)
                    elif fname.get_count() < lname.get_count():
                        fnames.remove(fname)
                else:
                    prob_A = fname.get_count()
                    prob_B = lname.get_count()
                    print("Probability that it is a first name:", fname.get_count())
                    print("Label:", label)
                    print("Locations:", fname.get_location(), lname.get_location())
                    print("Is family name? ", self.is_family_name(lname, last, alternatives))
                    print("Is first name? ", self.is_first_name(fname, last))
            else:
                if lname == None:
                    print("Unable to find label from lastnames: ", label, lnames)
                if fname == None:
                    print("Unable to find label from firstnames: ", label, fnames)

            fnames.sort(key=lambda x: x.get_string_start(), reverse=False)
            lnames.sort(key=lambda x: x.get_string_start(), reverse=False)
            #lname_list = sorted(lnames, key=lambda x: x.string_start, reverse=False)
            #print("[COMPARE]",fnames, fname_list)
            #print("[COMPARE]",lnames, lname_list)
            return fnames, lnames

    def find_name(self, arr, label):
        for item in arr:
            #print("Search for label from item", label, item)
            if item.get_name().strip() == label.strip():
                return item

        return None

    def is_family_name(self, name, last, alternatives):
        other_types = [a.get_type() for a in alternatives if a.get_type() != name.get_type()]
        if name.get_type() == "Sukunimi" and name.get_location() == last:
            return True
        elif name.get_type() == "Sukunimi" and len(other_types) < 1:
            return True
        return False

    def is_first_name(self, name, last):
        #print("Location of first:", last, name.get_location(), name.get_type())
        if name.get_type() == "Etunimi" and ((last == 1 or name.get_location() < last) and name.get_location() < 5):
            return True
        else:
            if name.get_type() != "Etunimi":
                print("Type FAIL")
            if (last != 1 or name.get_location() > last):
                print("location and last FAIL")
            if name.get_location() >= 5:
                print("Too long, FAIL")
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

        #req = Request('GET', URL, params=params)
        resp = requests.get(URL, params=params, headers=headers, stream=True)

        #prepared = s.prepare_request(req)
        #print("Url:",prepared.url)

        #print("Header:", prepared.headers)
        #print("Body:", prepared.body)
        #resp = None
        try:
            #resp = s.send(prepared)
            if resp != None:
                print("Request parameters:", params)
                print("Response status:", resp.status_code)
                print("RESPONSE header:", resp.headers)
                print("RESPONSE raw:", resp.raw)
                print("RESPONSE content:", resp.content)
                print("RESPONSE request URL:", resp.url)
            else:
                print("Raw response")
            data = resp.json()
        except requests.ConnectionError as ce:
            print("Unable to open with native function. Error: "  + str(ce))
        except Exception as e:
            if resp != None:
                print("Unable to process a request:", resp, resp.text)
                return "Unknown", resp
            print(e)

            return "Unknown", resp

        print(data)

        if 'gender' in data['results']:
            return data['results']['gender'], resp
        else:
            return "Unknown", resp

    def query_dates(self, string):

        print("CHECK DATE")

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
        URL = self.regex_url

        # defining a params dict for the parameters to be sent to the API
        params = {'text': string}

        # header
        headers = {'content-type': 'application/json'}

        #req = Request('GET', URL, params=params)
        resp = requests.get(URL, params=params, headers=headers, stream=True)

        #prepared = s.prepare_request(req)
        #print("Url:",prepared.url)

        #print("Header:", prepared.headers)
        #print("Body:", prepared.body)
        #resp = None
        try:
            #resp = s.send(prepared)
            if resp != None:
                print("Request parameters:", params)
                print("Response status:", resp.status_code)
                print("RESPONSE header:", resp.headers)
                print("RESPONSE raw:", resp.raw)
                print("RESPONSE content:", resp.content)
                print("RESPONSE request URL:", resp.url)
            else:
                print("Raw response")
            resultset = resp.json()
            data = None
            if resultset['status'] == 200:
                data = resultset['data']
        except requests.ConnectionError as ce:
            print("Unable to open with native function. Error: "  + str(ce))
        except Exception as e:
            if resp != None:
                print("Unable to process a request:", resp, resp.text)
                #return "Unknown 1", resp
            print(e)

            return "Unknown 2", resp

        print("DATA:",data)
        results = dict()

        if data != None:
            for key,item in data.items():
                print('Item:',item)
                for i in item['entities']:
                    if 'category' in i and 'entity' in i:
                        if i['category'] == 'DATETIME':
                            start = i['start_index']
                            end = i['end_index']
                            if 'string' not in results:
                                results[string] = list()
                            results[string].append((i['entity'], start, end))
                        else:
                            print("Wrong type:", item['entities'])
                else:
                    print("Unable to find entity in results:", item['entities'])

        return results, resp


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
        print("place:"+str(place))

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
        return {'name':str(self.original_form), 'lemma':str(self.label), 'type':str(self.clarify_type()), 'location':str(self.location), 'uri':self.name_uri, 'start_ind':self.string_start, 'end_ind':self.string_end}

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



