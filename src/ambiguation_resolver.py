class AmbiguityResolver():
    def __init__(self):
        self.full_names = None
        self.ambiguous_names = dict()

    def set_full_name(self, value):
        if value != None:
            self.full_names = value

    def get_ambiguous_names(self):
        return self.ambiguous_names

    def ambiguity_solver(self):
        single_names, longer_names = self.get_single_names()
        for single in single_names:
            entity = single.get_full_name_entities()[0]
            if entity.get_ref_place() != None:
                # in case a name can also be a reference to a place: check if there are longer names containing the name
                related = self.find_name_in_names(entity, longer_names)

                # in case the single name entity occurs alone
                if related == None:
                    self.ambiguous_names[single.get_full_name_index()] = single
                    single.set_place_ambiguity(entity.get_ref_place())
            elif entity.get_ref_vocation() != None:
                # in case sentece starts with a name that can also be a title
                if entity.get_string_start() < 2:
                    related = self.find_name_in_names(entity, longer_names)

                    # in case the single name entity occurs alone
                    if related == None:
                        self.ambiguous_names[single.get_full_name_index()] = single
                        single.set_vocation_ambiguity(entity.get_ref_vocation())

    # given a list of names and a name that is being searched, look up if similar name is a part of name in list
    def find_name_in_names(self, search_name, names):
        for name in names:
            for entity in name.get_full_name_entities():
                if entity.if_names_related(search_name):
                    return name
        return None

    def find_family_name(self, names):
        for name in names:
            if name.clarify_type(lang='fi') == "Sukunimi":
                return name
        return None

    def get_single_names(self):
        singles = list()
        others = list()
        for full_name in self.full_names:
            if len(full_name.get_full_name_entities()) == 1:
                singles.append(full_name)
            else:
                others.append(full_name)

        return singles, others