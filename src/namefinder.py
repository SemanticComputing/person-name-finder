from src.sparqlqueries import SparqlQuries
import json
import string

class NameFinder:
    def __init__(self):
        self.sparql = SparqlQuries()
        self.last_names = dict()
        self.first_names = dict()

    def identify_name(self, name_strings):
        names = dict()
        for i,name_string in name_strings.items():
            self.last_names[i] = list()
            self.first_names[i] = list()

            arr_names = self.split_names_to_arr(name_string, i)
            queried_names = self.sparql.query_names(arr_names)
            nr = NameRidler(queried_names, arr_names)
            names[i] = nr.get_names()

        return names, 1

    def split_names_to_arr(self, name_string, j):
        names = name_string.split(" ")

        helper = list()
        binders = ['de', 'la', 'af', 'i', 'von', 'van', 'le', 'les', 'der', 'du', 'of', 'in', 'av']
        builder = ""
        prev = None
        next = None
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

            if name.lower() not in binders and len(builder) == 0:
                self.first_names[j].append(name)
            elif name.lower() in binders and len(builder) == 0:
                builder = name
            elif len(builder) > 0:
                builder = builder + " " + name
            elif i == last:
                if len(builder) > 0:
                    self.last_names[j].append(builder)
                else:
                    if name[0].isupper():
                        self.last_names[j].append(name)
            else:
                print("Unable to identify name:", name)

        if i == last:
            if len(builder) > 0:
                self.last_names[j].append(builder)
            else:
                self.last_names[j].append(name)

        print(self.first_names[j], self.last_names[j])

        return self.first_names[j] + self.last_names[j]

class NameRidler:
    def __init__(self, names, ordered_names):
        self.ord_names = ordered_names
        self.full_names = dict()

        self.parse(names)


    def get_names(self):

        entities = list()
        for name, arr in self.full_names.items():
            entity = dict()
            items = list()
            print("For name: ", name, arr)
            if len(name.strip()) > 0:
                entity['full_name'] = name.strip()
                for item in arr:
                    if item.get_json() not in items:
                        print("Item:", item)
                        items.append(item.get_json())
                entity['names'] = items
                entities.append(entity)
        return entities


    def parse(self, queried_names):
        arr = dict()
        helper_arr = dict()
        counter = 0
        label = ""
        prev = None
        name = None
        full_name = ""
        prev_names =list()
        for result in queried_names["results"]["bindings"]:
            #print(result)
            prev = name
            prev_names.append(label)
            label = str(result["label"]["value"])
            count = int(result["count"]["value"])
            type = str(result["nameLabel"]["value"])
            linkage = str(result["nameType"]["value"])

            if counter == 0:
                counter += 1
            elif prev.get_name() != label:
                counter += 1
            else:
                print("Name occured twice:", name, prev)

            if prev != None:
                if (prev.get_type() == "Sukunimen käyttö" and type == "Etunimen käyttö") and (prev.get_name().strip() != label.strip() and len(list(arr.keys()))>1):
                    counter = 1

                    argh, full_name = self.determine_name(arr, helper_arr)
                    print("Full name in the middle:", full_name, '[', prev.get_name().strip(), '], [', label.strip(),
                          ']')
                    self.full_names[full_name] = argh
                    arr = dict()
                    helper_arr = dict()
                    prev = None
                    name = None
                    full_name = ""

                if prev != None:
                    if label != prev.get_name():
                        full_name += label + " "

            #if prev == None and len(full_name) == 0:
            #    full_name = label + " "

            name = Name(label, count, type, counter, linkage)

            print("Adding name:", name, full_name)

            if counter not in helper_arr.keys():
                helper_arr[counter] = list()
            helper_arr[counter].append(name)

            if label not in arr.keys():
                arr[label] = list()
            arr[label].append(name)

        argh, full_name = self.determine_name(arr, helper_arr)

        print("Full name:", full_name)

        self.full_names[full_name] = self.full_names[full_name] = argh

        #return self.full_names #self.determine_name(arr, helper_arr)

    def determine_name(self, names, helper):
        family_names = list()
        first_names = list()
        last = len(helper)
        full_name = ""

        for loc, names in helper.items():
            for name in names:
                print("Process:", name)
                if self.is_family_name(name, last):
                    family_names.append(name)
                elif self.is_first_name(name, last):
                    first_names.append(name)
                else:
                    if name.get_type() == "Sukunimen käyttö" and name.get_location() > 1 and not(self.is_first_name(name, last)):
                        family_names.append(name)
                    else:
                        print("Unable to identify name", name)


        fnames = [fn.get_name() for fn in first_names]
        lnames = [fn.get_name() for fn in family_names]

        overlap = set(fnames).intersection(set(lnames))

        if len(overlap) > 0:
            print("Overlapping names:", overlap)
            for o in overlap:
                first_names, family_names = self.reduce_overlapping(o, first_names, family_names, last)

        print("Return names:", first_names + family_names)

        full = first_names + family_names
        full_name = ' '.join(str(e.get_name()) for e in full)
        return full, full_name

    def reduce_overlapping(self, label, fnames, lnames, last):
        if fnames != None and lnames != None:
            fname = self.find_name(fnames, label)
            lname = self.find_name(lnames, label)

            print(fname, lname)

            l_last = len(lnames)-1
            f_last = len(fnames)-1

            if fname != None and lname != None:
                if fname.get_location() == lname.get_location() and self.is_family_name(lname, last) and not(self.is_first_name(fname, last)):
                    fnames.remove(fname)
                elif fname.get_location() == lname.get_location() and not(self.is_family_name(lname, last)) and self.is_first_name(fname, last):
                    lnames.remove(lname)
                else:
                    print("Label:", label)
                    print("Locations:", fname.get_location(), lname.get_location())
                    print("Is family name? ", self.is_family_name(lname, last))
                    print("Is first name? ", self.is_first_name(fname, last))
            else:
                if lname == None:
                    print("Unable to find label from lastnames: ", label, lnames)
                if fname == None:
                    print("Unable to find label from firstnames: ", label, fnames)

            return fnames, lnames

    def find_name(self, arr, label):
        for item in arr:
            print("Search for label from item", label, item)
            if item.get_name().strip() == label.strip():
                return item

        return None

    def is_family_name(self, name, last):
        print("Location of last:", last)
        if name.get_type() == "Sukunimen käyttö" and name.get_location() == last:
            return True
        return False

    def is_first_name(self, name, last):
        print("Location of last:", last, name.get_location())
        if name.get_type() == "Etunimen käyttö" and (name.get_location() < last and name.get_location() < 5):
            return True
        return False


class Name:
    def __init__(self, label, count, type, location, linkage):
        self.label = label
        self.count = count
        self.type = type
        self.location = location
        self.linkage = linkage

    def get_link(self):
        return self.linkage

    def get_name(self):
        return self.label

    def get_count(self):
        return self.count

    def get_type(self):
        return self.type

    def get_location(self):
        return self.location

    def clarify_type(self, lang='fi'):
        if self.type == "Sukunimen käyttö":
            if lang == 'fi':
                return "Sukunimi"
            else:
                return "Last name"
        if self.type == "Etunimen käyttö":
            if lang == 'fi':
                return "Etunimi"
            else:
                return "First name"
        return self.type


    def get_json(self):
        return {'name':str(self.label), 'type':str(self.clarify_type()), 'location':str(self.location), 'uri':self.linkage}

    def __str__(self):
        return self.label + " (" + str(self.count) + "): " + self.type + " @ " + str(self.location)


