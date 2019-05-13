from SPARQLWrapper import SPARQLWrapper, JSON
from django.conf import settings
import re

from KnowledgeExtractionApp.serializers import RelationSerializer
from KnowledgeExtractionApp.models import Relation

SEPARATOR = [".", "!", "?", ":", "،", "؟"]


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
                words.append(next_word)
                self.__phrases.append(Phrase(words))
                next_word = next_word.get_next_word()


class Sparql:
    def __init__(self, string):
        self.__string = string
        self.__query_subject_object = ""
        self.__query_subject_subject = ""
        self.__sentences = []
        self.__phrases = []
        self.__relations = []
        self.__subject_object_list = []
        self.split_text()
        self.create_relations()
        self.create_query_subject_object()

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

    def create_relations(self):
        delete_phrases = []
        for index in range(len(self.__phrases) - 1):
            for sub_index in range(index + 1, len(self.__phrases)):
                first_phrase = self.__phrases[index]
                second_phrase = self.__phrases[sub_index]
                if self.check_phrases(first_phrase, second_phrase):
                    relations = Relation.objects.filter(subject=first_phrase, object=second_phrase)
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
                        self.__subject_object_list.append(subject_object)

                    relations = Relation.objects.filter(subject=second_phrase, object=first_phrase)
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
                        self.__subject_object_list.append(subject_object)
        for phrase in delete_phrases:
            self.__phrases.remove(phrase)

    def create_query_subject_object(self):
        counter = 0
        self.__query_subject_object = "SELECT DISTINCT * WHERE{"
        for subject_object in self.__subject_object_list:
            print(subject_object.get_subject().get_string(), subject_object.get_object().get_string())
            subject_value = "{<" + settings.CONSTANTS["fkgr"] + subject_object.get_subject().get_string() + ">} "
            object_value = "{<" + settings.CONSTANTS["fkgr"] + subject_object.get_object().get_string() + ">} "
            mini_query = " {SELECT ?s, ?p, ?o WHERE{values ?s" + subject_value + "values ?o" + object_value + \
                         "?s ?p ?o FILTER(isIRI(?o))}} "
            # if self.__subject_object_list[-1] != subject_object:
            if counter != 20:
                mini_query += "UNION"
                self.__query_subject_object += mini_query
            else:
                self.__query_subject_object += mini_query
                break
            counter += 1
        self.__query_subject_object += "}"
        print(self.__query_subject_object)

    def check_phrases(self, phrase1, phrase2):
        for word1 in phrase1.get_words():
            for word2 in phrase2.get_words():
                if word1 == word2:
                    return False
        return True

    def check_relation(self, relation):
        for rel in self.__relations:
            if rel.subject == relation.subject and rel.predicate == relation.predicate and \
                    rel.object == relation.objects:
                return False
        return True

    def get_string(self):
        return self.__string

    def get_query_subject_object(self):
        return self.__query_subject_object

    def get_query_subject_subject(self):
        return self.__query_subject_subject

    def get_sentences(self):
        return self.__sentences

    def get_phrases(self):
        return self.__phrases

    def get_relations(self):
        return self.__relations

    def get_subject_object_list(self):
        return self.__subject_object_list

    def set_string(self, string):
        self.__string = string

    def set_query_subject_object(self, query_subject_object):
        self.__query_subject_object = query_subject_object

    def set_query_subject_subject(self, query_subject_subject):
        self.__query_subject_subject = query_subject_subject

    def set_sentences(self, sentences):
        self.__sentences = sentences

    def set_phrases(self, phrases):
        self.__phrases = phrases

    def set_relations(self, relations):
        self.__relations = relations

    def set_subject_object_list(self, subject_object_list):
        self.__subject_object_list = subject_object_list


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start


'''sparql = SPARQLWrapper(settings.CONSTANTS["SPARQL_URL"])
sparql.setQuery("""
    prefix fkgr: <http://fkg.iust.ac.ir/resource/>
    SELECT ?person
    WHERE {
        ?person fkgr:name "سلام"@fa .
    }

""")
sparql.setReturnFormat(JSON)
results = sparql.query().convert()
print(results)'''
