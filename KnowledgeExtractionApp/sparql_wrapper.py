import re
from urllib.error import URLError

from SPARQLWrapper import SPARQLWrapper, JSON
from django.conf import settings
from django.http import JsonResponse

from KnowledgeExtractionApp.models import Relation

SEPARATOR = [".", "!", "?", ":", "،", "؟"]
IGNORE_PREDICATES = [
    "http://dublincore.org/2012/06/14/dcterms#subject",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#instanceOf"
]


class SubjectObject:
    def __init__(self, subject, obj):
        self.__subject = subject
        self.__object = obj

    def get_subject(self):
        return self.__subject

    def get_object(self):
        return self.__object

    def set_subject(self, subject):
        self.__subject = subject

    def set_object(self, obj):
        self.__object = obj


class SubjectSubject:
    def __init__(self, first_subject, second_subject):
        self.__first_subject = first_subject
        self.__second_subject = second_subject

    def get_first_subject(self):
        return self.__first_subject

    def get_second_subject(self):
        return self.__second_subject

    def set_first_subject(self, first_subject):
        self.__first_subject = first_subject

    def set_second_subject(self, second_subject):
        self.__second_subject = second_subject


class Word:
    def __init__(self, string, next_word=None):
        self.__string = string
        self.__next_word = next_word

    def get_string(self):
        return self.__string

    def get_next_word(self):
        return self.__next_word

    def set_string(self, string):
        self.__string = string

    def set_next_word(self, next_word):
        self.__next_word = next_word


class Phrase:
    def __init__(self, words):
        self.__words = list(words)
        self.__string = ""
        self.__create_string()

    def get_string(self):
        return self.__string

    def get_words(self):
        return self.__words

    def set_string(self, string):
        self.__string = string

    def set_words(self, words):
        self.__words = words

    def __create_string(self):
        for index in range(len(self.__words) - 1):
            self.__string += self.__words[index].get_string()
            self.__string += "_"
        self.__string += self.__words[-1].get_string()


class Sentence:
    def __init__(self, string):
        self.__string = string
        self.__words = []
        self.__phrases = []
        self.__create_words()
        self.__create_phrases()

    def get_string(self):
        return self.__string

    def get_words(self):
        return self.__words

    def get_phrases(self):
        return self.__phrases

    def set_string(self, string):
        self.__string = string

    def set_words(self, words):
        self.__words = words

    def set_phrases(self, phrases):
        self.__phrases = phrases

    def __create_words(self):
        string_words = re.findall(r"[\w']+", self.__string)
        length_string_words = len(string_words)
        for index in range(length_string_words):
            self.__words.append(Word(string_words[index]))
        for index in range(length_string_words - 1):
            self.__words[index].set_next_word(self.__words[index + 1])

    def __create_phrases(self):
        for word in self.__words:
            words = [word]
            self.__phrases.append(Phrase(words))
            next_word = word.get_next_word()
            while next_word is not None:
                if len(words) == 4:
                    break
                words.append(next_word)
                self.__phrases.append(Phrase(words))
                next_word = next_word.get_next_word()


class Sparql:
    def __init__(self, string):
        self.__string = string
        self.__sparql_wrapper = SPARQLWrapper(settings.CONSTANTS["SPARQL_URL"])
        self.__sparql_wrapper.setReturnFormat(JSON)
        self.__query_existing_resources_list = []
        self.__query_subject_object_list = []
        self.__query_subject_subject_list = []
        self.__result_query = None
        self.__sentences = []
        self.__phrases = []
        self.__relations = []
        self.__subject_object_list = []
        self.__subject_subject_list = []
        self.split_text()
        self.check_resources()
        self.create_relations()
        self.create_query_subject_object()
        # self.create_query_subject_subject()

    def split_text(self):
        split_string = [self.__string]
        string_sentences = []
        for sep in SEPARATOR:
            tmp = []
            for data in split_string:
                split_data = data.split(sep)
                for data2 in split_data:
                    if data2 not in tmp:
                        tmp.append(data2)
            split_string = list(tmp)
        for i in range(len(split_string)):
            split_string[i] = split_string[i].strip()
            if split_string[i] != "":
                string_sentences.append(split_string[i])
        for string_sentence in string_sentences:
            sentence = Sentence(string_sentence)
            for phrase in sentence.get_phrases():
                if phrase not in self.__phrases:
                    self.__phrases.append(phrase)
            self.__sentences.append(sentence)

    def check_resources(self):
        phrases = list(self.__phrases)
        removing_phrases = []
        while True:
            counter = len(phrases)
            if counter > 100:
                counter = 100
            elif counter == 0:
                break
            phrases_mini_list = phrases[:counter]
            del phrases[:counter]
            query_existing_resources = "prefix fkgr: <%s> SELECT ?resource ?existing{values ?resource {"\
                                       % settings.CONSTANTS["fkgr"]
            for phrase in phrases_mini_list:
                query_existing_resources += "fkgr:%s " % phrase.get_string()
            query_existing_resources += "} bind (exists {?resource ?p ?o} AS ?existing)}"
            print(query_existing_resources)
            self.__query_existing_resources_list.append(query_existing_resources)
        for query_existing_resources in self.__query_existing_resources_list:
            query_index = self.__query_existing_resources_list.index(query_existing_resources)
            self.run_query(query_existing_resources)
            if self.__result_query:
                if "results" in self.__result_query:
                    if "bindings" in self.__result_query["results"]:
                        bindings = self.__result_query["results"]["bindings"]
                        for index in range(len(bindings)):
                            if bindings[index]['existing']['value'] == "0":
                                removing_phrases.append(self.__phrases[index + query_index * 100])
        for phrase in removing_phrases:
            if phrase in self.__phrases:
                self.__phrases.remove(phrase)

    def create_relations(self):
        delete_phrases = []
        for index in range(len(self.__phrases) - 1):
            for sub_index in range(index + 1, len(self.__phrases)):
                first_phrase = self.__phrases[index]
                second_phrase = self.__phrases[sub_index]
                if self.check_phrases(first_phrase, second_phrase):
                    relations = Relation.objects.filter(subject=first_phrase.get_string(),
                                                        object=second_phrase.get_string())
                    if len(relations) > 0:
                        for relation in relations:
                            if self.check_relation(relation):
                                self.__relations.append(relation)
                                if first_phrase not in delete_phrases:
                                    delete_phrases.append(first_phrase)
                                if second_phrase not in delete_phrases:
                                    delete_phrases.append(second_phrase)
                    else:
                        subject_object = SubjectObject(first_phrase, second_phrase)
                        subject_subject = SubjectSubject(first_phrase, second_phrase)
                        self.__subject_object_list.append(subject_object)
                        self.__subject_subject_list.append(subject_subject)

                    relations = Relation.objects.filter(subject=second_phrase.get_string(),
                                                        object=first_phrase.get_string())
                    if len(relations) > 0:
                        for relation in relations:
                            if self.check_relation(relation):
                                self.__relations.append(relation)
                                if first_phrase not in delete_phrases:
                                    delete_phrases.append(first_phrase)
                                if second_phrase not in delete_phrases:
                                    delete_phrases.append(second_phrase)
                    else:
                        subject_object = SubjectObject(second_phrase, first_phrase)
                        subject_subject = SubjectSubject(second_phrase, first_phrase)
                        self.__subject_object_list.append(subject_object)
                        self.__subject_subject_list.append(subject_subject)

        for phrase in delete_phrases:
            self.__phrases.remove(phrase)

    def create_query_subject_object(self):
        subject_object_list = list(self.__subject_object_list)
        while True:
            counter = len(subject_object_list)
            if counter > 10:
                counter = 10
            elif counter == 0:
                break
            subject_object_mini_list = subject_object_list[:counter]
            del subject_object_list[:counter]
            query_subject_object = "prefix fkgr: <%s> SELECT DISTINCT * WHERE{" % settings.CONSTANTS["fkgr"]
            for subject_object in subject_object_mini_list:
                subject_value = "{fkgr:%s}" % subject_object.get_subject().get_string()
                object_value = "{fkgr:%s}" % subject_object.get_object().get_string()
                mini_query = " {SELECT ?s, ?p, ?o WHERE{values ?s %s values ?o %s ?s ?p ?o FILTER(isIRI(?o))}} " %\
                             (subject_value, object_value)
                if subject_object_mini_list[-1] != subject_object:
                    mini_query += "UNION"
                    query_subject_object += mini_query
                else:
                    query_subject_object += mini_query
            query_subject_object += "}"
            self.__query_subject_object_list.append(query_subject_object)
        for query_subject_object in self.__query_subject_object_list:
            try:
                self.run_query(query_subject_object)
            except URLError:
                print("URLError")
                print(query_subject_object)
            if self.__result_query:
                if "results" in self.__result_query:
                    if "bindings" in self.__result_query["results"]:
                        fkgr_length = len(settings.CONSTANTS["fkgr"])
                        for item in self.__result_query["results"]["bindings"]:
                            relation = Relation.objects.create(
                                subject=item["s"]["value"][fkgr_length:],
                                object=item["o"]["value"][fkgr_length:],
                                predicate=item["p"]["value"])
                            self.__relations.append(relation)
                            relation.save()

    def create_query_subject_subject(self):
        subject_subject_list = list(self.__subject_subject_list)
        while True:
            counter = len(subject_subject_list)
            if counter > 10:
                counter = 10
            elif counter == 0:
                break
            subject_subject_mini_list = subject_subject_list[:counter]
            del subject_subject_list[:counter]
            query_subject_subject = "prefix fkgr: <%s> SELECT DISTINCT * WHERE{" % settings.CONSTANTS["fkgr"]
            for subject_subject in subject_subject_mini_list:
                first_subject_value = "{fkgr:%s}" % subject_subject.get_first_subject().get_string()
                second_subject_value = "{fkgr:%s}" % subject_subject.get_second_subject().get_string()
                mini_query = " {SELECT ?s1, ?s2, ?p, ?o WHERE{values ?s1 %s values ?s2 %s " \
                             "?s1 ?p ?o. ?s2 ?p ?o FILTER(isIRI(?o))}} " %\
                             (first_subject_value, second_subject_value)
                if subject_subject_mini_list[-1] != subject_subject:
                    mini_query += "UNION"
                    query_subject_subject += mini_query
                else:
                    query_subject_subject += mini_query
            query_subject_subject += "}"
            self.__query_subject_subject_list.append(query_subject_subject)
        for query_subject_subject in self.__query_subject_subject_list:
            try:
                self.run_query(query_subject_subject)
            except URLError:
                print("URLError")
                print(query_subject_subject)
            if self.__result_query:
                if "results" in self.__result_query:
                    if "bindings" in self.__result_query["results"]:
                        fkgr_length = len(settings.CONSTANTS["fkgr"])
                        for item in self.__result_query["results"]["bindings"]:
                            if item["p"]["value"] not in IGNORE_PREDICATES:
                                first_relation = Relation.objects.create(
                                    subject=item["s1"]["value"][fkgr_length:],
                                    object=item["o"]["value"][fkgr_length:],
                                    predicate=item["p"]["value"])
                                self.__relations.append(first_relation)
                                first_relation.save()

                                second_relation = Relation.objects.create(
                                    subject=item["s2"]["value"][fkgr_length:],
                                    object=item["o"]["value"][fkgr_length:],
                                    predicate=item["p"]["value"])
                                self.__relations.append(second_relation)
                                second_relation.save()

    def get_json_relations(self):
        json_relation_list = []
        for relation in self.__relations:
            json_relation = {"subject": relation.subject, "predicate": relation.predicate, "object": relation.object}
            json_relation_list.append(json_relation)

        return JsonResponse({"relations": json_relation_list})

    def run_query(self, query):
        self.__result_query = None
        self.__sparql_wrapper.setQuery(query)
        self.__result_query = self.__sparql_wrapper.query().convert()

    def check_phrases(self, phrase1, phrase2):
        for word1 in phrase1.get_words():
            for word2 in phrase2.get_words():
                if word1 == word2:
                    return False
        return True

    def check_relation(self, relation):
        for rel in self.__relations:
            if rel.subject == relation.subject and rel.predicate == relation.predicate and \
                    rel.object == relation.object:
                return False
        return True

    def get_string(self):
        return self.__string

    def get_sparql_wrapper(self):
        return self.__sparql_wrapper

    def get_query_existing_resources_list(self):
        return self.__query_existing_resources_list

    def get_query_subject_object(self):
        return self.__query_subject_object_list

    def get_query_subject_subject(self):
        return self.__query_subject_subject_list

    def get_result_query(self):
        return self.__result_query

    def get_sentences(self):
        return self.__sentences

    def get_phrases(self):
        return self.__phrases

    def get_relations(self):
        return self.__relations

    def get_subject_object_list(self):
        return self.__subject_object_list

    def get_subject_subject_list(self):
        return self.__subject_subject_list

    def set_string(self, string):
        self.__string = string

    def set_sparql_wrapper(self, sparql_wrapper):
        self.__sparql_wrapper = sparql_wrapper

    def set_query_existing_resources_list(self, query_existing_resources_list):
        self.__query_existing_resources_list = query_existing_resources_list

    def set_query_subject_object_list(self, query_subject_object_list):
        self.__query_subject_object_list = query_subject_object_list

    def set_query_subject_subject(self, query_subject_subject_list):
        self.__query_subject_subject_list = query_subject_subject_list

    def set_result_query(self, result_query):
        self.__result_query = result_query

    def set_sentences(self, sentences):
        self.__sentences = sentences

    def set_phrases(self, phrases):
        self.__phrases = phrases

    def set_relations(self, relations):
        self.__relations = relations

    def set_subject_object_list(self, subject_object_list):
        self.__subject_object_list = subject_object_list

    def set_subject_subject_list(self, subject_subject_list):
        self.__subject_subject_list = subject_subject_list


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start
