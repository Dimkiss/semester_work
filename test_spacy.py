import spacy

nlp = spacy.load("ru_core_news_lg")
print(nlp.pipe_labels["ner"])
